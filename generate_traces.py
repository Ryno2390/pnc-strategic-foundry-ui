#!/usr/bin/env python3
"""
PNC Strategic Foundry - S1 Reasoning Trace Generator
=====================================================

Generates reasoning traces from the S1 (Student) model for grading by Claude.
Part of the Self-Improving AI Flywheel architecture.

Usage:
    python generate_traces.py --prompts banking_prompts.jsonl --output s1_traces.jsonl
    python generate_traces.py --prompts banking_prompts.jsonl --limit 10  # Test with 10
    python generate_traces.py --interactive  # Single prompt testing

Requirements:
    - mlx-lm
    - Trained S1 adapter in ./s1_adapter/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("S1.Generator")


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class GeneratorConfig:
    """Configuration for the trace generator."""

    # Model settings
    base_model: str = "Qwen/Qwen2.5-3B-Instruct"
    adapter_path: str = "./s1_adapter"

    # Generation settings
    max_tokens: int = 1500  # Reasoning traces can be long
    temperature: float = 0.3  # Low temp for consistency, slight variation
    top_p: float = 0.9
    repetition_penalty: float = 1.05

    # File settings
    prompts_file: str = "./banking_prompts.jsonl"
    output_file: str = "./s1_traces.jsonl"

    # Processing settings
    limit: Optional[int] = None  # Limit number of prompts to process
    skip: int = 0  # Skip first N prompts (for resuming)
    verbose: bool = False


# =============================================================================
# System Prompt (Same as training)
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
</message>"""


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TraceResult:
    """Result of generating a single trace."""

    prompt_id: int
    category: str
    prompt: str
    response: str
    tokens_generated: int
    generation_time_sec: float
    tokens_per_second: float
    timestamp: str
    model_version: str = "s1_v1"
    grade: Optional[int] = None  # Filled in by grading step
    critique: Optional[str] = None  # Filled in by grading step

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Model Loader
# =============================================================================

class S1Model:
    """Wrapper for the S1 model with adapter."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the model with adapter."""
        try:
            from mlx_lm import load

            adapter_path = Path(self.config.adapter_path)

            if not adapter_path.exists():
                logger.error(f"Adapter not found at {adapter_path}")
                logger.error("Run train_s1.sh first to create the adapter.")
                sys.exit(1)

            logger.info(f"Loading {self.config.base_model} with S1 adapter...")
            start_time = time.time()

            self.model, self.tokenizer = load(
                self.config.base_model,
                adapter_path=str(adapter_path)
            )

            load_time = time.time() - start_time
            logger.info(f"Model loaded in {load_time:.1f}s")

        except ImportError:
            logger.error("mlx_lm not installed. Run: pip install mlx-lm")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            sys.exit(1)

    def generate(self, prompt: str) -> tuple[str, int, float]:
        """
        Generate a response for the given prompt.

        Returns:
            Tuple of (response, tokens_generated, generation_time)
        """
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        # Build chat messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        # Apply chat template
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Create sampler with temperature and top_p
        sampler = make_sampler(
            temp=self.config.temperature,
            top_p=self.config.top_p,
        )

        # Generate
        start_time = time.time()

        response = generate(
            self.model,
            self.tokenizer,
            prompt=formatted_prompt,
            max_tokens=self.config.max_tokens,
            sampler=sampler,
            verbose=self.config.verbose,
        )

        generation_time = time.time() - start_time
        tokens_generated = len(self.tokenizer.encode(response))

        return response, tokens_generated, generation_time


# =============================================================================
# Prompt Loader
# =============================================================================

def load_prompts(
    file_path: str,
    limit: Optional[int] = None,
    skip: int = 0
) -> Generator[dict, None, None]:
    """Load prompts from JSONL file."""

    path = Path(file_path)
    if not path.exists():
        logger.error(f"Prompts file not found: {file_path}")
        sys.exit(1)

    count = 0
    skipped = 0

    with open(path, "r") as f:
        for line in f:
            if skipped < skip:
                skipped += 1
                continue

            if limit and count >= limit:
                break

            try:
                data = json.loads(line.strip())
                yield data
                count += 1
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON line: {e}")
                continue

    logger.info(f"Loaded {count} prompts (skipped {skip})")


# =============================================================================
# Trace Generator
# =============================================================================

class TraceGenerator:
    """Generates reasoning traces from S1."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.model = S1Model(config)
        self.results: list[TraceResult] = []

    def generate_all(self) -> list[TraceResult]:
        """Generate traces for all prompts."""

        prompts = list(load_prompts(
            self.config.prompts_file,
            limit=self.config.limit,
            skip=self.config.skip
        ))

        total = len(prompts)
        logger.info(f"Generating traces for {total} prompts...")
        logger.info("=" * 60)

        start_time = time.time()

        for i, prompt_data in enumerate(prompts, 1):
            prompt_id = prompt_data.get("id", i)
            category = prompt_data.get("category", "unknown")
            prompt_text = prompt_data.get("prompt", "")

            logger.info(f"[{i}/{total}] Processing prompt {prompt_id} ({category})")

            try:
                response, tokens, gen_time = self.model.generate(prompt_text)
                tps = tokens / gen_time if gen_time > 0 else 0

                result = TraceResult(
                    prompt_id=prompt_id,
                    category=category,
                    prompt=prompt_text,
                    response=response,
                    tokens_generated=tokens,
                    generation_time_sec=round(gen_time, 2),
                    tokens_per_second=round(tps, 1),
                    timestamp=datetime.now().isoformat(),
                )

                self.results.append(result)

                # Log progress
                has_reasoning = "<reasoning>" in response.lower()
                has_message = "<message>" in response.lower()
                status = "OK" if (has_reasoning and has_message) else "WARN"

                logger.info(
                    f"    Generated {tokens} tokens in {gen_time:.1f}s "
                    f"({tps:.1f} tok/s) [{status}]"
                )

            except Exception as e:
                logger.error(f"    Failed: {e}")
                # Create error result
                result = TraceResult(
                    prompt_id=prompt_id,
                    category=category,
                    prompt=prompt_text,
                    response=f"ERROR: {str(e)}",
                    tokens_generated=0,
                    generation_time_sec=0,
                    tokens_per_second=0,
                    timestamp=datetime.now().isoformat(),
                )
                self.results.append(result)

        total_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"Completed {len(self.results)} traces in {total_time:.1f}s")

        return self.results

    def save_results(self, output_path: Optional[str] = None) -> str:
        """Save results to JSONL file."""

        path = output_path or self.config.output_file

        with open(path, "w") as f:
            for result in self.results:
                f.write(json.dumps(result.to_dict()) + "\n")

        logger.info(f"Saved {len(self.results)} traces to {path}")
        return path

    def print_summary(self) -> None:
        """Print generation summary."""

        if not self.results:
            logger.warning("No results to summarize")
            return

        total_tokens = sum(r.tokens_generated for r in self.results)
        total_time = sum(r.generation_time_sec for r in self.results)
        avg_tps = total_tokens / total_time if total_time > 0 else 0

        # Check formatting
        well_formatted = sum(
            1 for r in self.results
            if "<reasoning>" in r.response.lower() and "<message>" in r.response.lower()
        )

        print("\n" + "=" * 60)
        print("GENERATION SUMMARY")
        print("=" * 60)
        print(f"Total prompts processed: {len(self.results)}")
        print(f"Total tokens generated:  {total_tokens:,}")
        print(f"Total generation time:   {total_time:.1f}s")
        print(f"Average tokens/second:   {avg_tps:.1f}")
        print(f"Well-formatted traces:   {well_formatted}/{len(self.results)} "
              f"({100*well_formatted/len(self.results):.0f}%)")
        print("=" * 60)

        # Category breakdown
        by_category = {}
        for r in self.results:
            cat = r.category
            by_category[cat] = by_category.get(cat, 0) + 1

        print("\nBy Category:")
        for cat, count in sorted(by_category.items()):
            print(f"  {cat}: {count}")

        print("\n" + "=" * 60)
        print("NEXT STEP: Grade these traces with Claude")
        print("  python grade_with_claude.py --traces", self.config.output_file)
        print("=" * 60 + "\n")


# =============================================================================
# Interactive Mode
# =============================================================================

def run_interactive(config: GeneratorConfig) -> None:
    """Run interactive single-prompt testing."""

    print("\n" + "=" * 60)
    print("S1 Interactive Mode")
    print("Type a prompt and see S1's reasoning trace.")
    print("Type 'quit' to exit.")
    print("=" * 60 + "\n")

    model = S1Model(config)

    while True:
        try:
            prompt = input("\nPrompt> ").strip()

            if prompt.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if not prompt:
                continue

            print("\nGenerating trace...\n")
            response, tokens, gen_time = model.generate(prompt)
            tps = tokens / gen_time if gen_time > 0 else 0

            print("-" * 60)
            print(response)
            print("-" * 60)
            print(f"\n[{tokens} tokens in {gen_time:.1f}s ({tps:.1f} tok/s)]")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate reasoning traces with S1 model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate traces for all prompts
    python generate_traces.py

    # Generate traces for first 10 prompts (testing)
    python generate_traces.py --limit 10

    # Resume from prompt 50
    python generate_traces.py --skip 50

    # Custom input/output files
    python generate_traces.py --prompts my_prompts.jsonl --output my_traces.jsonl

    # Interactive single-prompt testing
    python generate_traces.py --interactive
        """
    )

    parser.add_argument(
        "--prompts", "-p",
        default="./banking_prompts.jsonl",
        help="Path to prompts JSONL file"
    )
    parser.add_argument(
        "--output", "-o",
        default="./s1_traces.jsonl",
        help="Path to output traces JSONL file"
    )
    parser.add_argument(
        "--adapter",
        default="./s1_adapter",
        help="Path to S1 adapter directory"
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Base model name"
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        help="Limit number of prompts to process"
    )
    parser.add_argument(
        "--skip", "-s",
        type=int,
        default=0,
        help="Skip first N prompts (for resuming)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1500,
        help="Maximum tokens to generate per response"
    )
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.3,
        help="Generation temperature (0.0-1.0)"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode for testing"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output during generation"
    )

    args = parser.parse_args()

    # Build config
    config = GeneratorConfig(
        base_model=args.model,
        adapter_path=args.adapter,
        prompts_file=args.prompts,
        output_file=args.output,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        limit=args.limit,
        skip=args.skip,
        verbose=args.verbose,
    )

    # Run interactive or batch mode
    if args.interactive:
        run_interactive(config)
    else:
        generator = TraceGenerator(config)
        generator.generate_all()
        generator.save_results()
        generator.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
