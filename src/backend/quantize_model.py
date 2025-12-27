#!/usr/bin/env python3
"""
PNC Strategic Foundry - Automated Model Quantization Pipeline
==============================================================

Converts fine-tuned or base models into memory-efficient quantized formats 
(4-bit/8-bit) optimized for Apple Silicon (MLX) and the macOS Advisor App.

Usage:
    python quantize_model.py --model ./outputs/pnc-strategic-advisor --bits 4
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd):
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return False

def quantize(model_path: str, output_path: str, bits: int):
    """Perform MLX-LM quantization."""
    print(f"\n--- Starting {bits}-bit Quantization ---")
    print(f"Source: {model_path}")
    print(f"Target: {output_path}")
    
    # MLX-LM command for quantization
    # Format: python -m mlx_lm.convert --hf-path <model> -q --q-bits <bits> --mlx-path <output>
    cmd = [
        sys.executable, "-m", "mlx_lm.convert",
        "--hf-path", model_path,
        "-q",
        "--q-bits", str(bits),
        "--mlx-path", output_path
    ]
    
    return run_command(cmd)

def main():
    parser = argparse.ArgumentParser(description="Automated Model Quantization")
    parser.add_argument("--model", type=str, required=True, help="Path to the model or HF repo")
    parser.add_argument("--bits", type=int, choices=[4, 8], default=4, help="Quantization bits")
    parser.add_argument("--output", type=str, help="Custom output directory")
    
    args = parser.parse_args()
    
    model_path = Path(args.model)
    if not model_path.exists() and not args.model.startswith("meta-llama/"):
        print(f"Error: Model path {args.model} does not exist.")
        sys.exit(1)
        
    output_dir = args.output or f"./outputs/{model_path.name}-{args.bits}bit"
    
    success = quantize(args.model, output_dir, args.bits)
    
    if success:
        print(f"\n✅ SUCCESS: Quantized model saved to {output_dir}")
        print(f"Next: Update AdvisorViewModel.swift in PNCAdvisor to point to this directory.")
    else:
        print("\n❌ FAILED: Quantization failed.")

if __name__ == "__main__":
    main()
