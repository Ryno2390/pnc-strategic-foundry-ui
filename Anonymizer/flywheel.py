#!/usr/bin/env python3
"""
PNC Strategic Foundry - Flywheel Command Center
================================================

Central orchestrator for the Self-Improving AI Flywheel.

The Flywheel Loop:
    1. TRAIN:    Fine-tune S1 with current training data
    2. GENERATE: Generate reasoning traces with S1
    3. GRADE:    Grade traces with Claude API
    4. UPDATE:   Add high-quality traces to training data
    5. REPEAT:   Retrain S1 with expanded dataset

Commands:
    python flywheel.py train      # Run S1 training
    python flywheel.py generate   # Generate traces with S1
    python flywheel.py grade      # Grade traces with Claude
    python flywheel.py loop       # Run complete flywheel cycle
    python flywheel.py status     # Show current state
    python flywheel.py merge      # Merge high-quality traces into training

Requirements:
    - mlx-lm (pip install mlx-lm)
    - anthropic (pip install anthropic)
    - ANTHROPIC_API_KEY environment variable
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Flywheel")


# =============================================================================
# Constants
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
ADAPTER_DIR = PROJECT_ROOT / "s1_adapter"

# Files
TRAIN_DATA = DATA_DIR / "train.jsonl"
VALID_DATA = DATA_DIR / "valid.jsonl"
HIGH_QUALITY_DATA = DATA_DIR / "high_quality.jsonl"
NEAR_MISS_DATA = DATA_DIR / "near_miss.jsonl"
PROMPTS_FILE = PROJECT_ROOT / "banking_prompts.jsonl"
TRACES_FILE = PROJECT_ROOT / "s1_traces.jsonl"
GRADED_FILE = PROJECT_ROOT / "graded_traces.jsonl"
STATE_FILE = PROJECT_ROOT / ".flywheel_state.json"


# =============================================================================
# State Management
# =============================================================================

@dataclass
class FlywheelState:
    """Tracks the current state of the flywheel."""

    iteration: int = 0
    last_train_time: Optional[str] = None
    last_generate_time: Optional[str] = None
    last_grade_time: Optional[str] = None

    # Cumulative statistics
    total_traces_generated: int = 0
    total_traces_graded: int = 0
    total_high_quality: int = 0
    total_near_miss: int = 0
    total_discarded: int = 0

    # Current training data size
    current_training_examples: int = 0

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "last_train_time": self.last_train_time,
            "last_generate_time": self.last_generate_time,
            "last_grade_time": self.last_grade_time,
            "total_traces_generated": self.total_traces_generated,
            "total_traces_graded": self.total_traces_graded,
            "total_high_quality": self.total_high_quality,
            "total_near_miss": self.total_near_miss,
            "total_discarded": self.total_discarded,
            "current_training_examples": self.current_training_examples,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FlywheelState:
        return cls(**data)


def load_state() -> FlywheelState:
    """Load flywheel state from file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return FlywheelState.from_dict(json.load(f))
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
    return FlywheelState()


def save_state(state: FlywheelState) -> None:
    """Save flywheel state to file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


# =============================================================================
# Helper Functions
# =============================================================================

def count_lines(path: Path) -> int:
    """Count lines in a file."""
    if not path.exists():
        return 0
    with open(path, "r") as f:
        return sum(1 for _ in f)


def run_command(cmd: list[str], cwd: Path = PROJECT_ROOT) -> tuple[int, str]:
    """Run a shell command and return exit code and output."""
    logger.info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        return result.returncode, output
    except Exception as e:
        return 1, str(e)


def activate_venv() -> dict:
    """Get environment with virtual environment activated."""
    env = os.environ.copy()
    venv_path = PROJECT_ROOT / ".venv"
    if venv_path.exists():
        env["VIRTUAL_ENV"] = str(venv_path)
        env["PATH"] = f"{venv_path}/bin:{env.get('PATH', '')}"
    return env


# =============================================================================
# Commands
# =============================================================================

def cmd_train(args: argparse.Namespace) -> int:
    """Run S1 training."""
    logger.info("=" * 60)
    logger.info("FLYWHEEL: Starting S1 Training")
    logger.info("=" * 60)

    state = load_state()

    # Check training data exists
    if not TRAIN_DATA.exists():
        logger.error(f"Training data not found: {TRAIN_DATA}")
        return 1

    examples = count_lines(TRAIN_DATA)
    logger.info(f"Training examples: {examples}")

    # Run training script
    train_script = PROJECT_ROOT / "train_s1.sh"
    if not train_script.exists():
        logger.error(f"Training script not found: {train_script}")
        return 1

    # Execute with --auto flag
    cmd = ["bash", str(train_script), "--auto"]

    logger.info("Starting training... This may take 15-30 minutes on M4.")

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        env=activate_venv(),
    )

    if result.returncode == 0:
        logger.info("Training completed successfully!")
        state.last_train_time = datetime.now().isoformat()
        state.current_training_examples = examples
        save_state(state)
        return 0
    else:
        logger.error("Training failed!")
        return result.returncode


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate reasoning traces with S1."""
    logger.info("=" * 60)
    logger.info("FLYWHEEL: Generating Reasoning Traces")
    logger.info("=" * 60)

    state = load_state()

    # Check adapter exists
    if not ADAPTER_DIR.exists():
        logger.error(f"S1 adapter not found: {ADAPTER_DIR}")
        logger.error("Run 'python flywheel.py train' first")
        return 1

    # Build command
    generate_script = PROJECT_ROOT / "generate_traces.py"
    cmd = [
        sys.executable, str(generate_script),
        "--prompts", str(PROMPTS_FILE),
        "--output", str(TRACES_FILE),
    ]

    if args.limit:
        cmd.extend(["--limit", str(args.limit)])

    # Run generation
    logger.info(f"Generating traces from {PROMPTS_FILE}")

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        env=activate_venv(),
    )

    if result.returncode == 0:
        traces_count = count_lines(TRACES_FILE)
        logger.info(f"Generated {traces_count} traces to {TRACES_FILE}")
        state.last_generate_time = datetime.now().isoformat()
        state.total_traces_generated += traces_count
        save_state(state)
        return 0
    else:
        logger.error("Trace generation failed!")
        return result.returncode


def cmd_grade(args: argparse.Namespace) -> int:
    """Grade traces with Claude API."""
    logger.info("=" * 60)
    logger.info("FLYWHEEL: Grading Traces with Claude")
    logger.info("=" * 60)

    state = load_state()

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY not set")
        logger.error("Set it with: export ANTHROPIC_API_KEY='your-key'")
        return 1

    # Check traces exist
    if not TRACES_FILE.exists():
        logger.error(f"Traces file not found: {TRACES_FILE}")
        logger.error("Run 'python flywheel.py generate' first")
        return 1

    # Build command
    grade_script = PROJECT_ROOT / "grade_with_claude.py"
    cmd = [
        sys.executable, str(grade_script),
        "--traces", str(TRACES_FILE),
        "--output", str(GRADED_FILE),
    ]

    if args.limit:
        cmd.extend(["--limit", str(args.limit)])

    # Run grading
    traces_count = count_lines(TRACES_FILE)
    logger.info(f"Grading {traces_count} traces with Claude...")

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        env=activate_venv(),
    )

    if result.returncode == 0:
        # Count results by tier
        high_quality = count_lines(HIGH_QUALITY_DATA)
        near_miss = count_lines(NEAR_MISS_DATA)

        state.last_grade_time = datetime.now().isoformat()
        state.total_traces_graded += traces_count
        state.total_high_quality += high_quality
        state.total_near_miss += near_miss
        save_state(state)

        logger.info(f"Grading complete!")
        logger.info(f"  High quality: {high_quality}")
        logger.info(f"  Near miss: {near_miss}")
        return 0
    else:
        logger.error("Grading failed!")
        return result.returncode


def cmd_merge(args: argparse.Namespace) -> int:
    """Merge high-quality traces into training data."""
    logger.info("=" * 60)
    logger.info("FLYWHEEL: Merging High-Quality Traces")
    logger.info("=" * 60)

    state = load_state()

    # Check high-quality data exists
    if not HIGH_QUALITY_DATA.exists():
        logger.error(f"High-quality data not found: {HIGH_QUALITY_DATA}")
        logger.error("Run grading first to generate high-quality traces")
        return 1

    new_count = count_lines(HIGH_QUALITY_DATA)
    if new_count == 0:
        logger.warning("No high-quality traces to merge")
        return 0

    current_count = count_lines(TRAIN_DATA)
    logger.info(f"Current training examples: {current_count}")
    logger.info(f"New high-quality traces: {new_count}")

    # Backup current training data
    backup_path = DATA_DIR / f"train_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    shutil.copy(TRAIN_DATA, backup_path)
    logger.info(f"Backed up training data to: {backup_path}")

    # Append high-quality traces to training data
    with open(TRAIN_DATA, "a") as train_file:
        with open(HIGH_QUALITY_DATA, "r") as hq_file:
            for line in hq_file:
                train_file.write(line)

    final_count = count_lines(TRAIN_DATA)
    logger.info(f"Training data expanded: {current_count} -> {final_count}")

    # Clear high-quality file (already merged)
    HIGH_QUALITY_DATA.unlink()

    state.current_training_examples = final_count
    state.iteration += 1
    save_state(state)

    logger.info("Merge complete! Ready for next training iteration.")
    return 0


def cmd_loop(args: argparse.Namespace) -> int:
    """Run complete flywheel cycle."""
    logger.info("=" * 60)
    logger.info("FLYWHEEL: Starting Complete Cycle")
    logger.info("=" * 60)

    state = load_state()
    logger.info(f"Current iteration: {state.iteration}")
    logger.info("")

    # Step 1: Generate traces
    logger.info("Step 1/3: Generating traces...")
    if cmd_generate(args) != 0:
        logger.error("Generation failed, aborting cycle")
        return 1

    # Step 2: Grade traces
    logger.info("")
    logger.info("Step 2/3: Grading traces...")
    if cmd_grade(args) != 0:
        logger.error("Grading failed, aborting cycle")
        return 1

    # Step 3: Merge if high-quality traces found
    logger.info("")
    hq_count = count_lines(HIGH_QUALITY_DATA) if HIGH_QUALITY_DATA.exists() else 0

    if hq_count > 0:
        logger.info(f"Step 3/3: Merging {hq_count} high-quality traces...")
        if cmd_merge(args) != 0:
            logger.error("Merge failed")
            return 1

        # Prompt for retraining
        logger.info("")
        logger.info("=" * 60)
        logger.info("CYCLE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Added {hq_count} new training examples")
        logger.info("")
        logger.info("To complete the flywheel, retrain S1:")
        logger.info("  python flywheel.py train")
        logger.info("")
    else:
        logger.info("Step 3/3: No high-quality traces to merge")
        logger.info("")
        logger.info("Consider reviewing near-miss traces for improvement opportunities.")

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show current flywheel status."""
    state = load_state()

    print("\n" + "=" * 60)
    print("PNC STRATEGIC FOUNDRY - FLYWHEEL STATUS")
    print("=" * 60)

    # Iteration info
    print(f"\nCurrent Iteration: {state.iteration}")

    # File status
    print("\nFile Status:")
    files = [
        ("Training Data", TRAIN_DATA),
        ("Validation Data", VALID_DATA),
        ("S1 Adapter", ADAPTER_DIR),
        ("Banking Prompts", PROMPTS_FILE),
        ("S1 Traces", TRACES_FILE),
        ("Graded Traces", GRADED_FILE),
        ("High Quality Queue", HIGH_QUALITY_DATA),
        ("Near Miss Queue", NEAR_MISS_DATA),
    ]

    for name, path in files:
        if path.exists():
            if path.is_dir():
                status = "EXISTS"
            else:
                lines = count_lines(path)
                status = f"{lines} examples"
        else:
            status = "NOT FOUND"
        print(f"  {name:20s}: {status}")

    # Timestamps
    print("\nLast Operations:")
    print(f"  Training:   {state.last_train_time or 'Never'}")
    print(f"  Generation: {state.last_generate_time or 'Never'}")
    print(f"  Grading:    {state.last_grade_time or 'Never'}")

    # Cumulative stats
    print("\nCumulative Statistics:")
    print(f"  Traces Generated: {state.total_traces_generated}")
    print(f"  Traces Graded:    {state.total_traces_graded}")
    print(f"  High Quality:     {state.total_high_quality}")
    print(f"  Near Miss:        {state.total_near_miss}")
    print(f"  Discarded:        {state.total_discarded}")

    # Training data growth
    print(f"\nTraining Data: {state.current_training_examples} examples")

    # Next steps
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)

    if not ADAPTER_DIR.exists():
        print("  1. Run initial training: python flywheel.py train")
    elif not TRACES_FILE.exists():
        print("  1. Generate traces: python flywheel.py generate")
    elif not GRADED_FILE.exists():
        print("  1. Grade traces: python flywheel.py grade")
    elif HIGH_QUALITY_DATA.exists() and count_lines(HIGH_QUALITY_DATA) > 0:
        print("  1. Merge and retrain: python flywheel.py merge")
        print("  2. Then: python flywheel.py train")
    else:
        print("  1. Run full cycle: python flywheel.py loop")

    print("=" * 60 + "\n")

    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean generated files for fresh start."""
    logger.info("Cleaning generated files...")

    files_to_clean = [
        TRACES_FILE,
        GRADED_FILE,
        HIGH_QUALITY_DATA,
        NEAR_MISS_DATA,
        STATE_FILE,
    ]

    for path in files_to_clean:
        if path.exists():
            path.unlink()
            logger.info(f"  Removed: {path}")

    logger.info("Clean complete. Training data and adapter preserved.")
    return 0


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="PNC Strategic Foundry - Flywheel Command Center",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The Flywheel Loop:
    1. TRAIN    -> Fine-tune S1 on current training data
    2. GENERATE -> Create reasoning traces with S1
    3. GRADE    -> Score traces with Claude (costs ~$0.01/trace)
    4. MERGE    -> Add high-quality traces to training data
    5. REPEAT   -> Retrain S1 with expanded dataset

Examples:
    # Check current status
    python flywheel.py status

    # Run individual stages
    python flywheel.py train
    python flywheel.py generate
    python flywheel.py grade
    python flywheel.py merge

    # Run complete cycle (generate -> grade -> merge)
    python flywheel.py loop

    # Test with limited data
    python flywheel.py generate --limit 5
    python flywheel.py grade --limit 5

    # Clean up generated files
    python flywheel.py clean
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show flywheel status")
    status_parser.set_defaults(func=cmd_status)

    # Train command
    train_parser = subparsers.add_parser("train", help="Run S1 training")
    train_parser.set_defaults(func=cmd_train)

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate traces with S1")
    gen_parser.add_argument("--limit", "-n", type=int, help="Limit prompts to process")
    gen_parser.set_defaults(func=cmd_generate)

    # Grade command
    grade_parser = subparsers.add_parser("grade", help="Grade traces with Claude")
    grade_parser.add_argument("--limit", "-n", type=int, help="Limit traces to grade")
    grade_parser.set_defaults(func=cmd_grade)

    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge high-quality traces")
    merge_parser.set_defaults(func=cmd_merge)

    # Loop command
    loop_parser = subparsers.add_parser("loop", help="Run complete flywheel cycle")
    loop_parser.add_argument("--limit", "-n", type=int, help="Limit traces per step")
    loop_parser.set_defaults(func=cmd_loop)

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean generated files")
    clean_parser.set_defaults(func=cmd_clean)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
