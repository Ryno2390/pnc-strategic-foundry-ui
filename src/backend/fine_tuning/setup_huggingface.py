"""
HuggingFace Setup Script for Llama 3.1 Access

This script helps you authenticate with HuggingFace and verify
you have access to the Llama 3.1 model.

Prerequisites:
1. Create a HuggingFace account: https://huggingface.co/join
2. Accept the Llama 3.1 license: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
3. Create an access token: https://huggingface.co/settings/tokens

Usage:
    source fine_tuning_env/bin/activate
    python fine_tuning/setup_huggingface.py
"""

import os
import sys
from huggingface_hub import HfApi, login, whoami


def check_login():
    """Check if user is logged in to HuggingFace."""
    try:
        user_info = whoami()
        return user_info
    except Exception:
        return None


def verify_model_access(model_id: str = "meta-llama/Llama-3.1-8B-Instruct"):
    """Verify access to the Llama model."""
    api = HfApi()
    try:
        model_info = api.model_info(model_id)
        return True, model_info
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 60)
    print("HuggingFace Setup for PNC Global Intelligence Foundry")
    print("=" * 60)

    # Check current login status
    print("\n→ Checking HuggingFace authentication...")
    user_info = check_login()

    if user_info:
        print(f"✓ Logged in as: {user_info['name']}")
    else:
        print("✗ Not logged in to HuggingFace")
        print("\nTo log in, you need a HuggingFace access token.")
        print("1. Go to: https://huggingface.co/settings/tokens")
        print("2. Create a new token (read access is sufficient)")
        print("3. Enter the token below:\n")

        login()

        # Verify login worked
        user_info = check_login()
        if user_info:
            print(f"\n✓ Successfully logged in as: {user_info['name']}")
        else:
            print("\n✗ Login failed. Please try again.")
            sys.exit(1)

    # Check model access
    print("\n→ Verifying access to Llama 3.1 8B Instruct...")
    model_id = "meta-llama/Llama-3.1-8B-Instruct"
    has_access, info = verify_model_access(model_id)

    if has_access:
        print(f"✓ Access verified for: {model_id}")
        print(f"  Model size: ~{info.safetensors.total / 1e9:.1f}GB")
    else:
        print(f"✗ Cannot access {model_id}")
        print(f"\nError: {info}")
        print("\n" + "=" * 60)
        print("ACTION REQUIRED:")
        print("=" * 60)
        print("1. Go to: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct")
        print("2. Log in to your HuggingFace account")
        print("3. Accept the Llama 3.1 license agreement")
        print("4. Wait a few minutes for access to propagate")
        print("5. Run this script again")
        print("=" * 60)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ Setup Complete!")
    print("=" * 60)
    print("\nYou are ready to run fine-tuning:")
    print("  python fine_tuning/pnc_finetune.py")
    print("\nOr test inference with the base model:")
    print("  python fine_tuning/inference.py")


if __name__ == "__main__":
    main()
