#!/usr/bin/env python3
"""
PNC Strategic Foundry - Teacher Injection
==========================================

Uses Claude (Teacher) to generate gold-standard training examples directly.
This "seeds" the flywheel with high-quality signal to overcome the cold-start problem.

The generated examples are saved in MLX-LM training format and can be merged
into the training data to bootstrap S1 quality.

Usage:
    python teacher_injection.py --count 20
    python teacher_injection.py --count 10 --category retail
    python teacher_injection.py --count 30 --merge  # Generate and merge into training

Requirements:
    - anthropic (pip install anthropic)
    - ANTHROPIC_API_KEY environment variable
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Teacher.Injection")


# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"
PROMPTS_FILE = PROJECT_ROOT / "banking_prompts.jsonl"
OUTPUT_FILE = PROJECT_ROOT / "teacher_examples.jsonl"
TRAIN_FILE = DATA_DIR / "train.jsonl"


@dataclass
class InjectionConfig:
    """Configuration for teacher injection."""

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2000
    temperature: float = 0.3  # Slight variation for diversity

    count: int = 20  # Number of examples to generate
    category: Optional[str] = None  # Filter by category (retail/commercial/wealth)

    output_file: str = str(OUTPUT_FILE)
    merge: bool = False  # Whether to merge into training data

    delay: float = 0.5  # Delay between API calls


# =============================================================================
# System Prompt (Same as S1 training)
# =============================================================================

SYSTEM_PROMPT = """You are a PNC Strategic Advisor. Your goal is to provide high-fidelity financial analysis. Before responding, you must perform a 'Reasoning Trace' using these steps:

1. Data Extraction: Identify the core financial facts provided in the input.
2. Regulatory Check: Cross-reference the request against standard bank policies and regulations.
3. Logical Modeling: Perform calculations or trend analysis step-by-step.
4. UI Planning: Determine which "Flash UI" components best represent this data.
5. Critique: Identify one potential risk or "hallucination point" in your own logic.

Output Format:
- Wrap your reasoning in <reasoning> tags
- Wrap your final user-facing response in <message> tags

Example structure:
<reasoning>
1. Data: [extracted facts]
2. Policy: [regulatory considerations]
3. Logic: [step-by-step analysis]
4. UI: [planned components]
5. Critique: [self-identified risks]
</reasoning>

<message>
[User-facing response with Flash UI components]
</message>

IMPORTANT GUIDELINES FOR HIGH-QUALITY RESPONSES:

1. ACCURACY: Use specific, realistic numbers. If the user provides a placeholder like <CURRENCY_VALUE>, interpret it as a reasonable amount (e.g., $15,000 for personal debt, $500,000 for business loans, $2M for wealth management). Show your math step-by-step.

2. POLICY COMPLIANCE: Reference specific regulations where relevant:
   - Retail: Truth in Lending Act (TILA), RESPA, Fair Credit Reporting Act
   - Commercial: SBA regulations, UCC, BSA/AML requirements
   - Wealth: SEC regulations, FINRA rules, fiduciary standards

3. FORMATTING: Always use the exact 5-step structure in <reasoning> tags, then provide the response in <message> tags.

4. UI QUALITY: Use realistic Flash UI components with concrete props:
   - <AmortizationTable rate="6.5%" term="360" principal="250000" />
   - <CashFlowChart months="12" data={[...]} />
   - <ComparisonCard options={[{name: "Option A", value: 1234}, ...]} />
   - <RiskIndicator level="moderate" factors={["market", "credit"]} />
   - <TimelineView milestones={[{date: "2024-Q1", event: "..."}]} />"""


# =============================================================================
# Claude Client
# =============================================================================

class TeacherModel:
    """Claude as the Teacher model."""

    def __init__(self, config: InjectionConfig):
        self.config = config
        self.client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.error("ANTHROPIC_API_KEY not set")
                sys.exit(1)

            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"Claude API initialized (model: {self.config.model})")

        except ImportError:
            logger.error("anthropic not installed. Run: pip install anthropic")
            sys.exit(1)

    def generate(self, prompt: str) -> tuple[str, int]:
        """
        Generate a gold-standard response for the given prompt.

        Returns:
            Tuple of (response, tokens_used)
        """
        try:
            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response = message.content[0].text
            tokens = message.usage.input_tokens + message.usage.output_tokens

            return response, tokens

        except Exception as e:
            logger.error(f"API error: {e}")
            return "", 0


# =============================================================================
# Prompt Selection
# =============================================================================

def load_prompts(
    file_path: Path,
    category: Optional[str] = None,
    count: int = 20
) -> list[dict]:
    """Load and select prompts for injection."""

    if not file_path.exists():
        logger.error(f"Prompts file not found: {file_path}")
        sys.exit(1)

    prompts = []
    with open(file_path, "r") as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if category is None or data.get("category") == category:
                    prompts.append(data)
            except json.JSONDecodeError:
                continue

    logger.info(f"Found {len(prompts)} prompts" +
                (f" in category '{category}'" if category else ""))

    # Select diverse sample
    if len(prompts) <= count:
        selected = prompts
    else:
        # Stratified sampling by category if no filter
        if category is None:
            by_cat = {}
            for p in prompts:
                cat = p.get("category", "unknown")
                by_cat.setdefault(cat, []).append(p)

            # Take proportional samples from each category
            selected = []
            per_cat = max(1, count // len(by_cat))
            for cat, cat_prompts in by_cat.items():
                selected.extend(random.sample(cat_prompts, min(per_cat, len(cat_prompts))))

            # Fill remaining slots randomly
            remaining = [p for p in prompts if p not in selected]
            if len(selected) < count and remaining:
                selected.extend(random.sample(remaining, min(count - len(selected), len(remaining))))
        else:
            selected = random.sample(prompts, count)

    random.shuffle(selected)
    return selected[:count]


# =============================================================================
# Injection Pipeline
# =============================================================================

class TeacherInjection:
    """Generates gold-standard examples using Claude."""

    def __init__(self, config: InjectionConfig):
        self.config = config
        self.teacher = TeacherModel(config)
        self.results: list[dict] = []
        self.total_tokens = 0

    def run(self) -> list[dict]:
        """Generate gold-standard examples."""

        prompts = load_prompts(
            PROMPTS_FILE,
            category=self.config.category,
            count=self.config.count
        )

        total = len(prompts)
        logger.info(f"Generating {total} gold-standard examples with Claude...")
        logger.info("=" * 60)

        for i, prompt_data in enumerate(prompts, 1):
            prompt_id = prompt_data.get("id", i)
            category = prompt_data.get("category", "unknown")
            prompt_text = prompt_data.get("prompt", "")

            logger.info(f"[{i}/{total}] Generating example {prompt_id} ({category})")

            response, tokens = self.teacher.generate(prompt_text)
            self.total_tokens += tokens

            if response:
                # Check quality
                has_reasoning = "<reasoning>" in response.lower()
                has_message = "<message>" in response.lower()
                status = "OK" if (has_reasoning and has_message) else "WARN"

                # Create training example in MLX-LM format
                example = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt_text},
                        {"role": "assistant", "content": response}
                    ],
                    "metadata": {
                        "source": "teacher_injection",
                        "teacher_model": self.config.model,
                        "prompt_id": prompt_id,
                        "category": category,
                        "generated_at": datetime.now().isoformat()
                    }
                }

                self.results.append(example)
                logger.info(f"    Generated {tokens} tokens [{status}]")
            else:
                logger.warning(f"    Failed to generate")

            # Rate limiting
            if i < total:
                time.sleep(self.config.delay)

        logger.info("=" * 60)
        logger.info(f"Generated {len(self.results)} examples")
        logger.info(f"Total tokens used: {self.total_tokens:,}")

        return self.results

    def save(self) -> str:
        """Save generated examples to file."""

        output_path = Path(self.config.output_file)

        with open(output_path, "w") as f:
            for example in self.results:
                f.write(json.dumps(example) + "\n")

        logger.info(f"Saved {len(self.results)} examples to {output_path}")
        return str(output_path)

    def merge_into_training(self) -> int:
        """Merge generated examples into training data."""

        if not self.results:
            logger.warning("No examples to merge")
            return 0

        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)

        # Count existing examples
        existing_count = 0
        if TRAIN_FILE.exists():
            with open(TRAIN_FILE, "r") as f:
                existing_count = sum(1 for _ in f)

        # Append new examples
        with open(TRAIN_FILE, "a") as f:
            for example in self.results:
                f.write(json.dumps(example) + "\n")

        new_count = existing_count + len(self.results)
        logger.info(f"Training data expanded: {existing_count} -> {new_count} examples")

        return len(self.results)

    def print_summary(self) -> None:
        """Print generation summary."""

        if not self.results:
            return

        # Category breakdown
        by_category = {}
        for r in self.results:
            cat = r["metadata"]["category"]
            by_category[cat] = by_category.get(cat, 0) + 1

        # Estimate cost (Claude Sonnet: ~$3/1M input, ~$15/1M output)
        estimated_cost = self.total_tokens * 0.000015  # Rough average

        print("\n" + "=" * 60)
        print("TEACHER INJECTION SUMMARY")
        print("=" * 60)
        print(f"Examples generated: {len(self.results)}")
        print(f"Total tokens:       {self.total_tokens:,}")
        print(f"Estimated cost:     ${estimated_cost:.3f}")
        print()
        print("By Category:")
        for cat, count in sorted(by_category.items()):
            print(f"  {cat}: {count}")
        print()
        print(f"Output file: {self.config.output_file}")

        if self.config.merge:
            print(f"Merged into: {TRAIN_FILE}")
        else:
            print()
            print("To merge into training data, run:")
            print(f"  python teacher_injection.py --merge --count 0")
            print("  # or re-run with --merge flag")

        print("=" * 60)
        print()
        print("NEXT STEP: Retrain S1 with expanded dataset")
        print("  python flywheel.py train")
        print("=" * 60 + "\n")


# =============================================================================
# Merge-Only Mode
# =============================================================================

def merge_existing() -> int:
    """Merge existing teacher_examples.jsonl into training data."""

    if not OUTPUT_FILE.exists():
        logger.error(f"No teacher examples found at {OUTPUT_FILE}")
        logger.error("Run teacher_injection.py first to generate examples")
        return 1

    # Load existing examples
    examples = []
    with open(OUTPUT_FILE, "r") as f:
        for line in f:
            try:
                examples.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    if not examples:
        logger.error("No valid examples found")
        return 1

    logger.info(f"Found {len(examples)} examples to merge")

    # Count existing training data
    existing_count = 0
    if TRAIN_FILE.exists():
        with open(TRAIN_FILE, "r") as f:
            existing_count = sum(1 for _ in f)

    # Append to training data
    DATA_DIR.mkdir(exist_ok=True)
    with open(TRAIN_FILE, "a") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    new_count = existing_count + len(examples)
    logger.info(f"Training data expanded: {existing_count} -> {new_count} examples")

    # Optionally clear the teacher examples file to prevent double-merge
    # OUTPUT_FILE.unlink()
    # logger.info(f"Cleared {OUTPUT_FILE} to prevent double-merge")

    return 0


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate gold-standard training examples using Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate 20 examples across all categories
    python teacher_injection.py --count 20

    # Generate 10 retail examples only
    python teacher_injection.py --count 10 --category retail

    # Generate and immediately merge into training
    python teacher_injection.py --count 20 --merge

    # Merge previously generated examples
    python teacher_injection.py --merge-only

    # Use a specific model
    python teacher_injection.py --count 10 --model claude-opus-4-20250514
        """
    )

    parser.add_argument(
        "--count", "-n",
        type=int,
        default=20,
        help="Number of examples to generate (default: 20)"
    )
    parser.add_argument(
        "--category", "-c",
        choices=["retail", "commercial", "wealth"],
        default=None,
        help="Filter prompts by category"
    )
    parser.add_argument(
        "--model", "-m",
        default="claude-sonnet-4-20250514",
        help="Claude model to use"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(OUTPUT_FILE),
        help="Output file for generated examples"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge generated examples into training data"
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Only merge existing examples (don't generate new ones)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API calls (seconds)"
    )

    args = parser.parse_args()

    # Check API key
    if not args.merge_only and not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nERROR: ANTHROPIC_API_KEY not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        return 1

    # Merge-only mode
    if args.merge_only:
        return merge_existing()

    # Build config
    config = InjectionConfig(
        model=args.model,
        count=args.count,
        category=args.category,
        output_file=args.output,
        merge=args.merge,
        delay=args.delay,
    )

    # Run injection
    injection = TeacherInjection(config)
    injection.run()
    injection.save()

    if config.merge:
        injection.merge_into_training()

    injection.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
