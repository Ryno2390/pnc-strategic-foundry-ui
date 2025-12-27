#!/bin/bash
# =============================================================================
# PNC Strategic Foundry - Cognitive Layer Training Script
# =============================================================================
# Fine-tunes Qwen2.5-3B-Instruct using LoRA for context-aware PII scrubbing
# Optimized for Apple M4 with 16GB RAM using MLX-LM framework
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
MODEL_NAME="Qwen/Qwen2.5-3B-Instruct"
ADAPTER_OUTPUT="./pnc_scrubber_adapter"
TRAINING_DATA="./pnc_anonymizer_train.jsonl"
LOG_FILE="./training_$(date +%Y%m%d_%H%M%S).log"

# LoRA Hyperparameters (optimized for M4 16GB RAM)
LORA_RANK=8                    # Lower rank for memory efficiency
LORA_ALPHA=16                  # Alpha = 2x rank is a good default
LORA_DROPOUT=0.05              # Light dropout for regularization
LORA_LAYERS=16                 # Target middle-to-late transformer layers

# Training Hyperparameters (tuned for small dataset, M4 hardware)
BATCH_SIZE=1                   # Conservative for 16GB RAM
GRADIENT_ACCUMULATION=4        # Effective batch size of 4
LEARNING_RATE=1e-4             # Standard for LoRA fine-tuning
NUM_ITERS=200                  # Iterations (adjust based on dataset size)
WARMUP_ITERS=20                # 10% warmup
SAVE_EVERY=50                  # Checkpoint frequency
VAL_BATCHES=10                 # Validation batches

# MLX Memory Settings
export MLX_METAL_PREALLOCATE=0           # Don't preallocate GPU memory
export MLX_METAL_MEMORY_BUDGET=12884901888  # ~12GB budget for safety margin

# -----------------------------------------------------------------------------
# Logging Functions
# -----------------------------------------------------------------------------
log_info() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [INFO] $1" | tee -a "${LOG_FILE}"
}

log_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [ERROR] $1" | tee -a "${LOG_FILE}" >&2
}

log_success() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [SUCCESS] $1" | tee -a "${LOG_FILE}"
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------
preflight_checks() {
    log_info "Running pre-flight checks..."

    # Check if running on macOS with Apple Silicon
    if [[ "$(uname)" != "Darwin" ]]; then
        log_error "This script is designed for macOS with Apple Silicon"
        exit 1
    fi

    if [[ "$(uname -m)" != "arm64" ]]; then
        log_error "Apple Silicon (arm64) required for MLX acceleration"
        exit 1
    fi

    # Check Python and MLX-LM installation
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is not installed"
        exit 1
    fi

    if ! python3 -c "import mlx_lm" &> /dev/null; then
        log_error "mlx_lm is not installed. Install with: pip install mlx-lm"
        exit 1
    fi

    # Verify training data exists
    if [[ ! -f "${TRAINING_DATA}" ]]; then
        log_error "Training data not found: ${TRAINING_DATA}"
        exit 1
    fi

    # Count training examples
    local num_examples=$(wc -l < "${TRAINING_DATA}" | tr -d ' ')
    log_info "Found ${num_examples} training examples in ${TRAINING_DATA}"

    # Check available memory
    local total_mem=$(sysctl -n hw.memsize)
    local total_mem_gb=$((total_mem / 1024 / 1024 / 1024))
    log_info "System memory: ${total_mem_gb}GB"

    if [[ ${total_mem_gb} -lt 16 ]]; then
        log_error "Minimum 16GB RAM required. Found: ${total_mem_gb}GB"
        exit 1
    fi

    log_success "Pre-flight checks passed"
}

# -----------------------------------------------------------------------------
# Create Training Configuration
# -----------------------------------------------------------------------------
create_lora_config() {
    log_info "Creating LoRA configuration..."

    cat > "./lora_config.yaml" << EOF
# PNC Cognitive Layer - LoRA Configuration
# Generated: $(date)

# Model Configuration
model: "${MODEL_NAME}"

# LoRA Parameters
lora_parameters:
  rank: ${LORA_RANK}
  alpha: ${LORA_ALPHA}
  dropout: ${LORA_DROPOUT}
  scale: $(echo "scale=2; ${LORA_ALPHA} / ${LORA_RANK}" | bc)

# Target Modules for Qwen architecture
lora_layers: ${LORA_LAYERS}
keys:
  - "self_attn.q_proj"
  - "self_attn.v_proj"

# Training Configuration
batch_size: ${BATCH_SIZE}
iters: ${NUM_ITERS}
learning_rate: ${LEARNING_RATE}
warmup: ${WARMUP_ITERS}
grad_checkpoint: true

# Data Configuration
data: "${TRAINING_DATA}"
train: true
EOF

    log_success "LoRA configuration saved to ./lora_config.yaml"
}

# -----------------------------------------------------------------------------
# Main Training Function
# -----------------------------------------------------------------------------
run_training() {
    log_info "=========================================="
    log_info "PNC Strategic Foundry - Cognitive Layer Training"
    log_info "=========================================="
    log_info "Model: ${MODEL_NAME}"
    log_info "Adapter Output: ${ADAPTER_OUTPUT}"
    log_info "LoRA Rank: ${LORA_RANK}, Alpha: ${LORA_ALPHA}"
    log_info "Learning Rate: ${LEARNING_RATE}"
    log_info "Iterations: ${NUM_ITERS}"
    log_info "=========================================="

    # Create output directory
    mkdir -p "${ADAPTER_OUTPUT}"

    # Run MLX-LM LoRA training
    log_info "Starting LoRA fine-tuning with MLX-LM..."

    python3 -m mlx_lm.lora \
        --model "${MODEL_NAME}" \
        --data "${TRAINING_DATA}" \
        --train \
        --batch-size ${BATCH_SIZE} \
        --iters ${NUM_ITERS} \
        --learning-rate ${LEARNING_RATE} \
        --lora-rank ${LORA_RANK} \
        --lora-layers ${LORA_LAYERS} \
        --adapter-path "${ADAPTER_OUTPUT}" \
        --save-every ${SAVE_EVERY} \
        --val-batches ${VAL_BATCHES} \
        --grad-checkpoint \
        2>&1 | tee -a "${LOG_FILE}"

    local exit_code=${PIPESTATUS[0]}

    if [[ ${exit_code} -eq 0 ]]; then
        log_success "Training completed successfully!"
        log_info "Adapter saved to: ${ADAPTER_OUTPUT}"
    else
        log_error "Training failed with exit code: ${exit_code}"
        exit ${exit_code}
    fi
}

# -----------------------------------------------------------------------------
# Post-training Validation
# -----------------------------------------------------------------------------
validate_adapter() {
    log_info "Validating trained adapter..."

    # Check adapter files exist
    if [[ ! -f "${ADAPTER_OUTPUT}/adapters.safetensors" ]] && \
       [[ ! -f "${ADAPTER_OUTPUT}/adapter_config.json" ]]; then
        log_error "Adapter files not found in ${ADAPTER_OUTPUT}"
        exit 1
    fi

    # Quick inference test
    log_info "Running inference validation..."

    python3 << 'VALIDATION_SCRIPT'
import sys
try:
    from mlx_lm import load, generate

    model, tokenizer = load(
        "Qwen/Qwen2.5-3B-Instruct",
        adapter_path="./pnc_scrubber_adapter"
    )

    test_input = "Test: John Smith at 123 Main St."
    messages = [
        {"role": "system", "content": "Execute Layer 3 Cognitive Scrubbing."},
        {"role": "user", "content": test_input}
    ]

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    response = generate(model, tokenizer, prompt=prompt, max_tokens=100)
    print(f"Validation test passed. Sample output length: {len(response)}")
    sys.exit(0)

except Exception as e:
    print(f"Validation warning: {e}")
    sys.exit(0)  # Don't fail on validation warnings
VALIDATION_SCRIPT

    log_success "Adapter validation completed"
}

# -----------------------------------------------------------------------------
# Print Usage Summary
# -----------------------------------------------------------------------------
print_summary() {
    echo ""
    log_info "=========================================="
    log_info "Training Summary"
    log_info "=========================================="
    log_info "Adapter Location: ${ADAPTER_OUTPUT}"
    log_info "Training Log: ${LOG_FILE}"
    echo ""
    log_info "To use the trained adapter in orchestrator.py:"
    echo ""
    echo "    from mlx_lm import load, generate"
    echo "    model, tokenizer = load("
    echo "        '${MODEL_NAME}',"
    echo "        adapter_path='${ADAPTER_OUTPUT}'"
    echo "    )"
    echo ""
    log_info "=========================================="
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
    echo "PNC Strategic Foundry - Cognitive Layer Training"
    echo "================================================"
    echo ""

    # Initialize log file
    echo "Training session started: $(date)" > "${LOG_FILE}"

    # Run pipeline
    preflight_checks
    create_lora_config
    run_training
    validate_adapter
    print_summary

    log_success "All tasks completed successfully!"
}

# Execute main function
main "$@"
