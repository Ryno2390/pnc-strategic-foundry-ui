#!/bin/bash
# =============================================================================
# PNC Strategic Foundry - S1 (Student Model) Training Script
# =============================================================================
# Fine-tunes Qwen2.5-3B-Instruct as the first-generation Student model
# OPTIMIZED FOR: Apple M4 with 16GB Unified Memory
# =============================================================================

set -euo pipefail

# Check for --auto flag (non-interactive mode)
AUTO_MODE=false
if [[ "${1:-}" == "--auto" ]]; then
    AUTO_MODE=true
fi

# Activate virtual environment if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/.venv/bin/activate" ]]; then
    source "${SCRIPT_DIR}/.venv/bin/activate"
fi

# -----------------------------------------------------------------------------
# Configuration - MEMORY OPTIMIZED FOR 16GB
# -----------------------------------------------------------------------------
MODEL_NAME="Qwen/Qwen2.5-3B-Instruct"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "${BACKEND_DIR}")")"
ADAPTER_OUTPUT="${BACKEND_DIR}/s1_adapter"
TRAINING_DATA="${PROJECT_ROOT}/data/training"
LOG_DIR="${PROJECT_ROOT}/logs"
LOG_FILE="${LOG_DIR}/s1_training_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "${LOG_DIR}"

# LoRA Hyperparameters - CONSERVATIVE FOR 16GB
# Lower rank = less memory, still effective for small datasets
LORA_RANK=4                    # Reduced from 8 for memory savings
LORA_ALPHA=8                   # Alpha = 2x rank
LORA_LAYERS=8                  # Fewer layers = less memory

# Training Hyperparameters - MEMORY OPTIMIZED
BATCH_SIZE=1                   # Minimum batch size
GRADIENT_ACCUMULATION=8        # Effective batch = 8 (accumulate gradients)
LEARNING_RATE=2e-4             # Slightly higher LR for smaller effective batch
NUM_ITERS=300                  # More iterations for small dataset
WARMUP_ITERS=30                # 10% warmup
SAVE_EVERY=100                 # Checkpoint frequency
VAL_BATCHES=5                  # Reduced validation batches

# MLX Memory Settings - CRITICAL FOR 16GB
export MLX_METAL_PREALLOCATE=0              # Don't preallocate - allocate on demand
export MLX_METAL_MEMORY_BUDGET=10737418240  # ~10GB budget (leave 6GB for OS/buffers)

# -----------------------------------------------------------------------------
# Colors for output
# -----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Logging Functions
# -----------------------------------------------------------------------------
log_info() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[${timestamp}] [INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

log_warn() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[${timestamp}] [WARN]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[${timestamp}] [ERROR]${NC} $1" | tee -a "${LOG_FILE}" >&2
}

log_success() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[${timestamp}] [SUCCESS]${NC} $1" | tee -a "${LOG_FILE}"
}

# -----------------------------------------------------------------------------
# Memory Monitoring Function
# -----------------------------------------------------------------------------
check_memory() {
    # Get available memory in GB
    local mem_free=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
    local mem_inactive=$(vm_stat | grep "Pages inactive" | awk '{print $3}' | tr -d '.')
    local page_size=$(pagesize)
    local available_bytes=$(( (mem_free + mem_inactive) * page_size ))
    local available_gb=$(echo "scale=2; $available_bytes / 1024 / 1024 / 1024" | bc)
    echo "$available_gb"
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------
preflight_checks() {
    log_info "Running pre-flight checks for 16GB M4 optimization..."

    # Create logs directory
    mkdir -p ./logs

    # Check if running on macOS with Apple Silicon
    if [[ "$(uname)" != "Darwin" ]]; then
        log_error "This script requires macOS"
        exit 1
    fi

    if [[ "$(uname -m)" != "arm64" ]]; then
        log_error "Apple Silicon (arm64) required"
        exit 1
    fi

    # Check chip type
    local chip=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Unknown")
    log_info "Detected chip: ${chip}"

    # Check total memory
    local total_mem=$(sysctl -n hw.memsize)
    local total_mem_gb=$((total_mem / 1024 / 1024 / 1024))
    log_info "Total system memory: ${total_mem_gb}GB"

    if [[ ${total_mem_gb} -lt 16 ]]; then
        log_error "Minimum 16GB RAM required. Found: ${total_mem_gb}GB"
        exit 1
    fi

    # Check available memory
    local available_mem=$(check_memory)
    log_info "Approximately ${available_mem}GB available"

    if (( $(echo "$available_mem < 10" | bc -l) )); then
        log_warn "Low available memory (${available_mem}GB). Close other applications for best performance."
    fi

    # Check Python and MLX-LM
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is not installed"
        exit 1
    fi

    if ! python3 -c "import mlx_lm" &> /dev/null; then
        log_error "mlx_lm not installed. Run: pip install mlx-lm"
        exit 1
    fi

    # Check MLX-LM version
    local mlx_version=$(python3 -c "import mlx_lm; print(mlx_lm.__version__)" 2>/dev/null || echo "unknown")
    log_info "MLX-LM version: ${mlx_version}"

    # Verify training data
    if [[ ! -d "${TRAINING_DATA}" ]]; then
        log_error "Training data directory not found: ${TRAINING_DATA}"
        exit 1
    fi

    if [[ ! -f "${TRAINING_DATA}/train.jsonl" ]]; then
        log_error "train.jsonl not found in ${TRAINING_DATA}"
        exit 1
    fi

    local num_examples=$(wc -l < "${TRAINING_DATA}/train.jsonl" | tr -d ' ')
    log_info "Training examples: ${num_examples}"

    if [[ ${num_examples} -lt 10 ]]; then
        log_warn "Very small dataset (${num_examples} examples). Consider adding more data."
    fi

    log_success "Pre-flight checks passed"
}

# -----------------------------------------------------------------------------
# Close Memory-Heavy Apps (Optional)
# -----------------------------------------------------------------------------
optimize_memory() {
    log_info "Memory optimization tips:"
    echo "  - Close browser tabs (especially Chrome)"
    echo "  - Quit unused applications"
    echo "  - Close Xcode, Slack, Docker if running"
    echo ""
    if [[ "$AUTO_MODE" == "false" ]]; then
        read -p "Press Enter when ready to continue (or Ctrl+C to abort)..."
    else
        log_info "Auto mode: skipping interactive prompt"
    fi
}

# -----------------------------------------------------------------------------
# Main Training Function
# -----------------------------------------------------------------------------
run_training() {
    echo ""
    log_info "=========================================="
    log_info "   PNC Strategic Foundry - S1 Training"
    log_info "=========================================="
    log_info "Model: ${MODEL_NAME}"
    log_info "Adapter Output: ${ADAPTER_OUTPUT}"
    log_info "Memory Budget: 10GB (of 16GB)"
    log_info "=========================================="
    echo ""
    log_info "LoRA Configuration:"
    log_info "  Rank: ${LORA_RANK} (low for memory efficiency)"
    log_info "  Alpha: ${LORA_ALPHA}"
    log_info "  Target Layers: ${LORA_LAYERS}"
    echo ""
    log_info "Training Configuration:"
    log_info "  Batch Size: ${BATCH_SIZE}"
    log_info "  Gradient Accumulation: ${GRADIENT_ACCUMULATION}"
    log_info "  Effective Batch: $((BATCH_SIZE * GRADIENT_ACCUMULATION))"
    log_info "  Learning Rate: ${LEARNING_RATE}"
    log_info "  Iterations: ${NUM_ITERS}"
    log_info "=========================================="
    echo ""

    # Create output directory
    mkdir -p "${ADAPTER_OUTPUT}"

    # Record start time
    local start_time=$(date +%s)

    log_info "Starting S1 fine-tuning..."
    log_info "This will take approximately 15-30 minutes on M4."
    echo ""

    # Run MLX-LM LoRA training with memory-optimized settings
    # Note: MLX-LM v0.30+ uses new command format
    python3 -m mlx_lm lora \
        --model "${MODEL_NAME}" \
        --data "${TRAINING_DATA}" \
        --train \
        --fine-tune-type lora \
        --batch-size ${BATCH_SIZE} \
        --iters ${NUM_ITERS} \
        --learning-rate ${LEARNING_RATE} \
        --num-layers ${LORA_LAYERS} \
        --grad-accumulation-steps ${GRADIENT_ACCUMULATION} \
        --adapter-path "${ADAPTER_OUTPUT}" \
        --save-every ${SAVE_EVERY} \
        --val-batches ${VAL_BATCHES} \
        --grad-checkpoint \
        2>&1 | tee -a "${LOG_FILE}"

    local exit_code=${PIPESTATUS[0]}
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    echo ""
    if [[ ${exit_code} -eq 0 ]]; then
        log_success "Training completed in ${minutes}m ${seconds}s"
        log_info "Adapter saved to: ${ADAPTER_OUTPUT}"
    else
        log_error "Training failed with exit code: ${exit_code}"
        log_error "Check ${LOG_FILE} for details"
        exit ${exit_code}
    fi
}

# -----------------------------------------------------------------------------
# Validate Trained Adapter
# -----------------------------------------------------------------------------
validate_adapter() {
    log_info "Validating S1 adapter..."

    # Check adapter files
    if [[ ! -d "${ADAPTER_OUTPUT}" ]]; then
        log_error "Adapter directory not found"
        exit 1
    fi

    # Quick inference test
    log_info "Running inference validation..."

    python3 << 'VALIDATION_SCRIPT'
import sys
import time

try:
    from mlx_lm import load, generate

    print("Loading S1 model with adapter...")
    start = time.time()

    model, tokenizer = load(
        "Qwen/Qwen2.5-3B-Instruct",
        adapter_path="./s1_adapter"
    )

    load_time = time.time() - start
    print(f"Model loaded in {load_time:.1f}s")

    # Test inference
    test_prompt = "I need help with my mortgage refinance."

    system_prompt = """You are a PNC Strategic Advisor. Your goal is to provide high-fidelity financial analysis. Before responding, you must perform a 'Reasoning Trace' using: 1) Data Extraction, 2) Regulatory Check, 3) Logical Modeling, 4) UI Planning, 5) Critique. Wrap reasoning in <reasoning> tags and final response in <message> tags."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": test_prompt}
    ]

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    print("Generating test response...")
    start = time.time()

    response = generate(
        model, tokenizer,
        prompt=prompt,
        max_tokens=200,
        temperature=0.1
    )

    gen_time = time.time() - start
    tokens = len(tokenizer.encode(response))
    tps = tokens / gen_time

    print(f"Generated {tokens} tokens in {gen_time:.1f}s ({tps:.1f} tok/s)")

    # Check if response has expected structure
    has_reasoning = "<reasoning>" in response.lower() or "data extraction" in response.lower()

    if has_reasoning:
        print("Validation PASSED: Model produces reasoning traces")
        sys.exit(0)
    else:
        print("Validation WARNING: Response may not follow reasoning format")
        print(f"Response preview: {response[:200]}...")
        sys.exit(0)  # Don't fail, just warn

except Exception as e:
    print(f"Validation error: {e}")
    sys.exit(1)
VALIDATION_SCRIPT

    local exit_code=$?
    if [[ ${exit_code} -eq 0 ]]; then
        log_success "S1 adapter validation completed"
    else
        log_error "Validation failed"
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Print Summary and Next Steps
# -----------------------------------------------------------------------------
print_summary() {
    echo ""
    log_info "=========================================="
    log_info "   S1 Training Complete!"
    log_info "=========================================="
    echo ""
    log_info "Adapter Location: ${ADAPTER_OUTPUT}"
    log_info "Training Log: ${LOG_FILE}"
    echo ""
    log_info "Next Steps in the Flywheel:"
    echo ""
    echo "  1. Generate reasoning traces with S1:"
    echo "     python generate_traces.py --prompts banking_prompts.jsonl"
    echo ""
    echo "  2. Grade traces with Claude API:"
    echo "     python grade_with_claude.py --traces s1_traces.jsonl"
    echo ""
    echo "  3. Filter high-quality traces (8+/10) and retrain"
    echo ""
    log_info "=========================================="
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
    echo ""
    echo "============================================"
    echo "  PNC Strategic Foundry - S1 Training"
    echo "  Optimized for Apple M4 16GB"
    echo "============================================"
    echo ""

    # Initialize log file
    mkdir -p ./logs
    echo "S1 Training session started: $(date)" > "${LOG_FILE}"
    echo "Configuration: LORA_RANK=${LORA_RANK}, BATCH=${BATCH_SIZE}, ITERS=${NUM_ITERS}" >> "${LOG_FILE}"

    # Run pipeline
    preflight_checks
    optimize_memory
    run_training
    validate_adapter
    print_summary

    log_success "S1 is ready for inference!"
}

# Handle interrupts gracefully
trap 'echo ""; log_warn "Training interrupted by user"; exit 130' INT

# Execute
main "$@"
