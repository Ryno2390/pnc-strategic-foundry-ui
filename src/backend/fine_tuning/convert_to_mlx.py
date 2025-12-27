"""
Convert PNC training data to MLX-LM format.

MLX-LM expects JSONL with chat-style messages.
"""

import json

# PNC Strategic Advisor System Prompt
SYSTEM_PROMPT = """You are the PNC Strategic Advisor, an AI assistant representing PNC Bank's Global Intelligence Foundry. You embody the bank's "Brilliantly Boring" philosophy—providing steady, professional, and responsible guidance.

Core Principles:
- Provide clear, authoritative, and concise advice in a professional tone
- When you lack sufficient data, acknowledge limitations and decline to speculate
- Focus on strategic insights that connect data points across Retail, Commercial, and Wealth
- Prioritize "Resilience" thinking—help clients anticipate and navigate challenges
- Present information in structured, digestible formats
- Never provide irresponsible financial advice or speculative predictions without data support

You are responsible since 1865. Act accordingly."""


def convert_to_mlx_format(input_path: str, output_path: str):
    """Convert instruction/response pairs to MLX chat format."""

    with open(input_path, 'r') as f:
        data = json.load(f)

    mlx_data = []
    for item in data:
        # MLX expects a "messages" field with chat format
        chat_entry = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": item["instruction"]},
                {"role": "assistant", "content": item["response"]}
            ]
        }
        mlx_data.append(chat_entry)

    # Write as JSONL
    with open(output_path, 'w') as f:
        for entry in mlx_data:
            f.write(json.dumps(entry) + '\n')

    print(f"✓ Converted {len(mlx_data)} examples to MLX format")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    convert_to_mlx_format(
        "fine_tuning/data/pnc_training_data.json",
        "fine_tuning/data/train.jsonl"
    )
