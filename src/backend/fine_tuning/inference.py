"""
PNC Strategic Advisor - Inference Script

Use this script to test your fine-tuned model or run inference.

Usage:
    source fine_tuning_env/bin/activate
    python fine_tuning/inference.py
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os

from pathlib import Path
INFERENCE_DIR = Path(__file__).parent
PROJECT_ROOT = INFERENCE_DIR.parent.parent

# Paths
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
ADAPTER_PATH = str(PROJECT_ROOT / "outputs" / "pnc-strategic-advisor")

# System prompt
SYSTEM_PROMPT = """You are the PNC Strategic Advisor, an AI assistant representing PNC Bank's Global Intelligence Foundry. You embody the bank's "Brilliantly Boring" philosophy—providing steady, professional, and responsible guidance.

Core Principles:
- Provide clear, authoritative, and concise advice in a professional tone
- When you lack sufficient data, acknowledge limitations and decline to speculate
- Focus on strategic insights that connect data points across Retail, Commercial, and Wealth
- Prioritize "Resilience" thinking—help clients anticipate and navigate challenges
- Present information in structured, digestible formats
- Never provide irresponsible financial advice or speculative predictions without data support

You are responsible since 1865. Act accordingly."""


def load_model(use_finetuned=True):
    """Load the model with optional fine-tuned LoRA adapters."""
    print("→ Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token

    print("→ Loading base model...")
    # Determine device
    if torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float16
    elif torch.cuda.is_available():
        device = "cuda"
        dtype = torch.float16
    else:
        device = "cpu"
        dtype = torch.float32

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )

    # Load fine-tuned adapters if available
    if use_finetuned and os.path.exists(ADAPTER_PATH):
        print("→ Loading fine-tuned LoRA adapters...")
        model = PeftModel.from_pretrained(model, ADAPTER_PATH)
        print("✓ Fine-tuned model loaded")
    else:
        print("✓ Base model loaded (no fine-tuning applied)")

    return model, tokenizer


def generate_response(model, tokenizer, user_input: str, max_length: int = 1024):
    """Generate a response using the Llama 3.1 chat format."""
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>

{user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_length,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.convert_tokens_to_ids("<|eot_id|>"),
        )

    response = tokenizer.decode(outputs[0], skip_special_tokens=False)
    # Extract just the assistant response
    if "<|start_header_id|>assistant<|end_header_id|>" in response:
        response = response.split("<|start_header_id|>assistant<|end_header_id|>")[-1]
        response = response.replace("<|eot_id|>", "").strip()

    return response


def interactive_session(model, tokenizer):
    """Run an interactive Q&A session."""
    print("\n" + "=" * 60)
    print("PNC Strategic Advisor - Interactive Session")
    print("=" * 60)
    print("Type 'quit' or 'exit' to end the session.")
    print("Type 'help' for example questions.\n")

    example_questions = [
        "What risks should I monitor for my manufacturing business?",
        "How should I structure my company's cash reserves?",
        "Can you predict the stock market performance?",
        "What are typical financial ratios for my industry?",
    ]

    while True:
        user_input = input("\n[You]: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit"]:
            print("\nThank you for using PNC Strategic Advisor. Goodbye.")
            break

        if user_input.lower() == "help":
            print("\nExample questions you can ask:")
            for i, q in enumerate(example_questions, 1):
                print(f"  {i}. {q}")
            continue

        print("\n[PNC Strategic Advisor]: ", end="")
        response = generate_response(model, tokenizer, user_input)
        print(response)


def main():
    print("=" * 60)
    print("PNC Global Intelligence Foundry - Inference")
    print("=" * 60)

    # Check if fine-tuned model exists
    use_finetuned = os.path.exists(ADAPTER_PATH)

    if use_finetuned:
        print(f"✓ Fine-tuned model found at: {ADAPTER_PATH}")
    else:
        print("ℹ No fine-tuned model found. Using base model with system prompt.")

    model, tokenizer = load_model(use_finetuned)
    interactive_session(model, tokenizer)


if __name__ == "__main__":
    main()
