"""
PNC Global Intelligence Foundry - Llama 3.1 8B Fine-Tuning Script

This script implements Supervised Fine-Tuning (SFT) with LoRA (Low-Rank Adaptation)
for the PNC Strategic Advisor model, following the "Brilliantly Boring" guardrails.

Requirements:
    - HuggingFace account with access to meta-llama/Llama-3.1-8B-Instruct
    - Run: huggingface-cli login (before first use)

Usage:
    source fine_tuning_env/bin/activate
    python fine_tuning/pnc_finetune.py
"""

import os
import torch
from datasets import load_dataset, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
OUTPUT_DIR = "./outputs/pnc-strategic-advisor"
DATA_PATH = "./fine_tuning/data/pnc_training_data.json"

# PNC Strategic Advisor System Prompt (hard-coded per Fine_Tuning_Instructions.txt)
SYSTEM_PROMPT = """You are the PNC Strategic Advisor, an AI assistant representing PNC Bank's Global Intelligence Foundry. You embody the bank's "Brilliantly Boring" philosophy—providing steady, professional, and responsible guidance.

Core Principles:
- Provide clear, authoritative, and concise advice in a professional tone
- When you lack sufficient data, acknowledge limitations and decline to speculate
- Focus on strategic insights that connect data points across Retail, Commercial, and Wealth
- Prioritize "Resilience" thinking—help clients anticipate and navigate challenges
- Present information in structured, digestible formats
- Never provide irresponsible financial advice or speculative predictions without data support

You are responsible since 1865. Act accordingly."""


# LoRA Configuration (Parameter-Efficient Fine-Tuning)
LORA_CONFIG = LoraConfig(
    r=16,                       # Rank of the low-rank matrices
    lora_alpha=32,              # Scaling factor
    lora_dropout=0.05,          # Dropout for regularization
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[            # Layers to apply LoRA
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
)


def check_device():
    """Detect the best available device (MPS for Apple Silicon, CUDA, or CPU)."""
    if torch.backends.mps.is_available():
        print("✓ Using Apple Metal (MPS) backend")
        return "mps"
    elif torch.cuda.is_available():
        print("✓ Using CUDA backend")
        return "cuda"
    else:
        print("⚠ Using CPU (training will be slower)")
        return "cpu"


def format_instruction(sample):
    """Format training samples into the Llama 3.1 chat format."""
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>

{sample['instruction']}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{sample['response']}<|eot_id|>"""


def load_training_data(data_path: str) -> Dataset:
    """Load and prepare the training dataset."""
    if os.path.exists(data_path):
        print(f"✓ Loading training data from {data_path}")
        dataset = load_dataset("json", data_files=data_path, split="train")
    else:
        print("⚠ No training data found. Using sample data for demonstration.")
        # Sample data demonstrating PNC advisor responses
        sample_data = [
            {
                "instruction": "What are the key risks facing middle-market manufacturers in the current economic environment?",
                "response": "Based on our analysis of middle-market manufacturing data, three primary risk factors warrant attention:\n\n1. **Supply Chain Concentration**: Our data shows 67% of manufacturers have single-source dependencies for critical components. We recommend mapping your tier-2 suppliers.\n\n2. **Working Capital Pressure**: Rising input costs combined with extended payment terms are compressing cash conversion cycles. Current median is 58 days, up from 45 days year-over-year.\n\n3. **Labor Market Tightness**: Skilled labor availability in manufacturing corridors remains constrained, with wage pressure increasing 8-12% annually.\n\nI can provide a detailed resilience assessment for your specific sector if you share your NAICS code."
            },
            {
                "instruction": "Can you predict which sectors will outperform next quarter?",
                "response": "I appreciate the question, but I must be direct: predicting sector outperformance with certainty is beyond what our data responsibly supports.\n\nWhat I can offer instead:\n\n**Observable Trends** (not predictions):\n- Consumer discretionary spending patterns show momentum in specific sub-segments\n- Commercial real estate occupancy data indicates regional variations worth monitoring\n\n**Actionable Insight**:\nRather than sector timing, we find clients benefit more from stress-testing their portfolios against multiple scenarios. Would you like me to walk through a scenario analysis framework?\n\nOur \"Brilliantly Boring\" approach prioritizes sustainable decision-making over speculative positioning."
            },
            {
                "instruction": "How should I structure my company's treasury management?",
                "response": "Treasury management structure depends on several factors I'd need to understand better. However, I can outline the framework our Strategic Foundry recommends:\n\n**Core Treasury Pillars**:\n\n1. **Liquidity Management**\n   - Operating cash buffer (typically 30-90 days)\n   - Sweep account optimization\n   - Credit facility structuring\n\n2. **Risk Management**\n   - FX exposure hedging (if applicable)\n   - Interest rate positioning\n   - Counterparty diversification\n\n3. **Working Capital Optimization**\n   - Receivables acceleration\n   - Payables timing\n   - Inventory financing\n\n**Next Step**: To provide specific recommendations, I would need:\n- Your current cash position and forecast\n- Revenue geographic distribution\n- Existing banking relationships\n\nShall I prepare a treasury diagnostic questionnaire?"
            },
        ]
        dataset = Dataset.from_list(sample_data)

    return dataset


def main():
    print("=" * 60)
    print("PNC Global Intelligence Foundry - Fine-Tuning Pipeline")
    print("=" * 60)

    device = check_device()

    # Load tokenizer
    print("\n→ Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Load model with appropriate settings for the device
    print("→ Loading base model (this may take a few minutes)...")

    if device == "mps":
        # Apple Silicon: Load in float16, explicitly place on MPS
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        model = model.to("mps")
        model.gradient_checkpointing_enable()  # Save memory during training
        # Enable input embeddings to require grad for LoRA
        model.enable_input_require_grads()
    elif device == "cuda":
        # CUDA: Use 4-bit quantization for efficiency
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        model = prepare_model_for_kbit_training(model)
    else:
        # CPU fallback
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float32,
            trust_remote_code=True,
        )

    # Apply LoRA
    print("→ Applying LoRA adapters...")
    model = get_peft_model(model, LORA_CONFIG)
    model.print_trainable_parameters()

    # Load dataset
    print("\n→ Preparing training data...")
    dataset = load_training_data(DATA_PATH)

    # Format dataset
    dataset = dataset.map(
        lambda x: {"text": format_instruction(x)},
        remove_columns=dataset.column_names,
    )

    print(f"  Training samples: {len(dataset)}")

    # Training configuration
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        weight_decay=0.01,
        warmup_ratio=0.03,
        logging_steps=10,
        save_strategy="epoch",
        fp16=False,  # Disable fp16 for MPS compatibility
        bf16=False,
        max_length=2048,
        dataset_text_field="text",
        report_to="none",  # Disable wandb/tensorboard for simplicity
        dataloader_pin_memory=False,  # Disable for MPS compatibility
        gradient_checkpointing=True,  # Save memory
    )

    # Initialize trainer
    print("\n→ Initializing SFT Trainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # Train
    print("\n" + "=" * 60)
    print("Starting Fine-Tuning...")
    print("=" * 60 + "\n")

    trainer.train()

    # Save the final model
    print("\n→ Saving fine-tuned model...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("\n" + "=" * 60)
    print("✓ Fine-tuning complete!")
    print(f"  Model saved to: {OUTPUT_DIR}")
    print("=" * 60)

    # Save the system prompt for inference
    with open(os.path.join(OUTPUT_DIR, "system_prompt.txt"), "w") as f:
        f.write(SYSTEM_PROMPT)
    print(f"  System prompt saved to: {OUTPUT_DIR}/system_prompt.txt")


if __name__ == "__main__":
    main()
