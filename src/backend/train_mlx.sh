#!/bin/bash
#PNC Strategic Foundry - Logic Distillation Trainer (MLX)
# ========================================================
# Distills the "Teacher" reasoning traces into the Local "Student" Model.
#
# Requirements:
# - Apple Silicon Mac (M1/M2/M3)
# - mlx-lm installed (pip install mlx-lm)
# - Valid training data at data/training/s1_distillation_train.jsonl

# Configuration
MODEL_NAME="Qwen/Qwen2.5-3B-Instruct" # The Student Model (Small, Fast)
DATA_PATH="data/training/s1_distillation_train.jsonl"
OUTPUT_ADAPTER="pnc_advisor_adapter"
ITERS=600 # Adjust based on dataset size (usually ~3 epochs)

echo "=================================================="
echo "PNC Strategic Foundry: Distilling Logic to Student"
echo "=================================================="
echo "Teacher Data: $DATA_PATH"
echo "Student Base: $MODEL_NAME"
echo "Target Adapter: $OUTPUT_ADAPTER"
echo "=================================================="

# Check if data exists
if [ ! -f "$DATA_PATH" ]; then
    echo "Error: Training data not found!"
    echo "Run 'python src/backend/synthetic_factory.py' first."
    exit 1
fi

# Run MLX LoRA Fine-Tuning
# --lora-layers 16: Fine-tune more layers for better reasoning
# --batch-size 4: Adjust based on VRAM (4 is safe for 16GB)
python -m mlx_lm.lora \
    --model $MODEL_NAME \
    --train \
    --data $DATA_PATH \
    --adapter-path $OUTPUT_ADAPTER \
    --iters $ITERS \
    --batch-size 4 \
    --learning-rate 1e-5 \
    --seed 42

echo "=================================================="
echo "Distillation Complete!"
echo "Adapter saved to: $OUTPUT_ADAPTER"
echo "To run the Student: use the --adapter flag in app.py"
echo "=================================================="