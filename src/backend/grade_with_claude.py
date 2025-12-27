#!/usr/bin/env python3
"""
PNC Strategic Foundry - Claude Grading Script
==============================================

Grades S1 reasoning traces using Claude API with a structured rubric.
Part of the Self-Improving AI Flywheel architecture.

Rubric Dimensions:
    1. Accuracy (1-10): Financial math and logic correctness
    2. Policy Compliance (1-10): Regulatory considerations mentioned
    3. Formatting (1-10): Correct <reasoning> and <message> tags
    4. UI Quality (1-10): Flash UI code validity and relevance

3-Tier Scoring System:
    - 8+/10: Add to training data (high quality)
    - 5-7/10: Near-miss log for analysis
    - <5/10: Discard

Usage:
    python grade_with_claude.py --traces s1_traces.jsonl
    python grade_with_claude.py --traces s1_traces.jsonl --limit 5
    python grade_with_claude.py --traces s1_traces.jsonl --output graded_traces.jsonl

Requirements:
    - anthropic (pip install anthropic)
    - ANTHROPIC_API_KEY environment variable
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Claude.Grader")


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class GraderConfig:
    """Configuration for the grading pipeline."""

    # API settings
    model: str = "claude-sonnet-4-20250514"  # Cost-effective for grading
    max_tokens: int = 1000
    temperature: float = 0.0  # Deterministic grading

    # File settings
    traces_file: str = "./s1_traces.jsonl"
    output_file: str = "./graded_traces.jsonl"
    training_file: str = "./data/high_quality.jsonl"  # 8+/10 traces
    nearmiss_file: str = "./data/near_miss.jsonl"     # 5-7/10 traces

    # Processing settings
    limit: Optional[int] = None
    skip: int = 0
    batch_delay: float = 0.5  # Seconds between API calls (rate limiting)

    # Thresholds
    high_quality_threshold: float = 8.0
    near_miss_min: float = 5.0


# =============================================================================
# Grading Rubric Prompt
# =============================================================================

GRADING_SYSTEM_PROMPT = """You are an expert evaluator for PNC Strategic Foundry's AI training pipeline.

Your task is to grade reasoning traces produced by an AI financial advisor (S1 model).
Grade each dimension on a scale of 1-10 and provide specific feedback.

## Rubric Dimensions

### 1. Accuracy (1-10)
- Financial calculations are mathematically correct
- Logic is sound and follows from premises
- Numbers referenced are consistent
- No contradictions in reasoning

Scoring guide:
- 1-3: Major errors, wrong calculations, illogical conclusions
- 4-6: Some errors, partially correct reasoning
- 7-8: Mostly correct, minor issues
- 9-10: Excellent accuracy, clear logical flow

### 2. Policy Compliance (1-10)
- Mentions regulatory considerations
- References bank policies appropriately
- Considers compliance requirements
- Flags potential regulatory issues

Scoring guide:
- 1-3: No regulatory awareness
- 4-6: Minimal policy mention, generic
- 7-8: Good regulatory awareness, specific policies
- 9-10: Excellent compliance integration, proactive flagging

### 3. Formatting (1-10)
- Uses <reasoning> tags correctly
- Uses <message> tags correctly
- Follows the 5-step reasoning structure:
  1. Data Extraction
  2. Regulatory Check
  3. Logical Modeling
  4. UI Planning
  5. Critique

Scoring guide:
- 1-3: Missing tags, no structure
- 4-6: Some structure, missing elements
- 7-8: Good structure, minor format issues
- 9-10: Perfect formatting, all 5 steps present

### 4. UI Quality (1-10)
- Flash UI components are appropriate for the context
- Component props are relevant and complete
- UI choices match the user's needs
- Components are realistic and implementable

Scoring guide:
- 1-3: No UI components or completely irrelevant
- 4-6: Basic UI, somewhat relevant
- 7-8: Good UI choices, well-structured
- 9-10: Excellent UI design, creative and appropriate

## Response Format

You MUST respond with valid JSON in this exact format:
{
    "accuracy": <1-10>,
    "policy_compliance": <1-10>,
    "formatting": <1-10>,
    "ui_quality": <1-10>,
    "overall_score": <average of above>,
    "tier": "<high_quality|near_miss|discard>",
    "feedback": {
        "accuracy_notes": "<specific feedback>",
        "policy_notes": "<specific feedback>",
        "formatting_notes": "<specific feedback>",
        "ui_notes": "<specific feedback>",
        "improvement_suggestions": "<how to improve>"
    }
}

Tier assignment:
- "high_quality": overall_score >= 8.0
- "near_miss": overall_score >= 5.0 and < 8.0
- "discard": overall_score < 5.0"""


GRADING_USER_TEMPLATE = """Please grade the following S1 reasoning trace:

## User Prompt
{prompt}

## S1 Response
{response}

Grade this trace according to the rubric and respond with the JSON evaluation."""


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class GradeResult:
    """Result of grading a single trace."""

    # Original trace data
    prompt_id: int
    category: str
    prompt: str
    response: str

    # Grading results
    accuracy: float
    policy_compliance: float
    formatting: float
    ui_quality: float
    overall_score: float
    tier: str  # high_quality, near_miss, discard

    # Feedback
    feedback: dict

    # Metadata
    graded_at: str
    grader_model: str
    original_tokens: int

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Claude API Client
# =============================================================================

class ClaudeGrader:
    """Grades traces using Claude API."""

    def __init__(self, config: GraderConfig):
        self.config = config
        self.client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.error("ANTHROPIC_API_KEY environment variable not set")
                logger.error("Set it with: export ANTHROPIC_API_KEY='your-key'")
                sys.exit(1)

            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"Claude API initialized (model: {self.config.model})")

        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            sys.exit(1)

    def grade_trace(self, prompt: str, response: str) -> dict:
        """
        Grade a single trace using Claude.

        Returns:
            Dictionary with grading results
        """
        user_message = GRADING_USER_TEMPLATE.format(
            prompt=prompt,
            response=response
        )

        try:
            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=GRADING_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            # Extract text content
            response_text = message.content[0].text

            # Parse JSON response
            return self._parse_grade_response(response_text)

        except Exception as e:
            logger.error(f"API call failed: {e}")
            return self._default_grade(str(e))

    def _parse_grade_response(self, response_text: str) -> dict:
        """Parse Claude's JSON response."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.warning("No JSON found in response")
                return self._default_grade("No JSON in response")
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return self._default_grade(f"JSON parse error: {e}")

    def _default_grade(self, error_msg: str) -> dict:
        """Return default grade on error."""
        return {
            "accuracy": 0,
            "policy_compliance": 0,
            "formatting": 0,
            "ui_quality": 0,
            "overall_score": 0,
            "tier": "discard",
            "feedback": {
                "accuracy_notes": f"Grading error: {error_msg}",
                "policy_notes": "",
                "formatting_notes": "",
                "ui_notes": "",
                "improvement_suggestions": ""
            }
        }


# =============================================================================
# Grading Pipeline
# =============================================================================

class GradingPipeline:
    """Orchestrates the grading process."""

    def __init__(self, config: GraderConfig):
        self.config = config
        self.grader = ClaudeGrader(config)
        self.results: list[GradeResult] = []

        # Statistics
        self.stats = {
            "high_quality": 0,
            "near_miss": 0,
            "discard": 0,
            "total_cost_estimate": 0.0
        }

    def load_traces(self) -> list[dict]:
        """Load traces from JSONL file."""
        path = Path(self.config.traces_file)
        if not path.exists():
            logger.error(f"Traces file not found: {path}")
            sys.exit(1)

        traces = []
        with open(path, "r") as f:
            for i, line in enumerate(f):
                if self.config.skip and i < self.config.skip:
                    continue
                if self.config.limit and len(traces) >= self.config.limit:
                    break
                try:
                    traces.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON on line {i+1}")

        logger.info(f"Loaded {len(traces)} traces to grade")
        return traces

    def grade_all(self) -> list[GradeResult]:
        """Grade all loaded traces."""
        traces = self.load_traces()
        total = len(traces)

        logger.info(f"Starting grading of {total} traces...")
        logger.info("=" * 60)

        for i, trace in enumerate(traces, 1):
            prompt_id = trace.get("prompt_id", i)
            category = trace.get("category", "unknown")
            prompt = trace.get("prompt", "")
            response = trace.get("response", "")
            original_tokens = trace.get("tokens_generated", 0)

            logger.info(f"[{i}/{total}] Grading prompt {prompt_id} ({category})")

            # Call Claude API
            grade_data = self.grader.grade_trace(prompt, response)

            # Create result
            result = GradeResult(
                prompt_id=prompt_id,
                category=category,
                prompt=prompt,
                response=response,
                accuracy=grade_data.get("accuracy", 0),
                policy_compliance=grade_data.get("policy_compliance", 0),
                formatting=grade_data.get("formatting", 0),
                ui_quality=grade_data.get("ui_quality", 0),
                overall_score=grade_data.get("overall_score", 0),
                tier=grade_data.get("tier", "discard"),
                feedback=grade_data.get("feedback", {}),
                graded_at=datetime.now().isoformat(),
                grader_model=self.config.model,
                original_tokens=original_tokens
            )

            self.results.append(result)
            self.stats[result.tier] += 1

            # Log result
            logger.info(
                f"    Score: {result.overall_score:.1f}/10 [{result.tier.upper()}] "
                f"(A:{result.accuracy} P:{result.policy_compliance} "
                f"F:{result.formatting} U:{result.ui_quality})"
            )

            # Rate limiting
            if i < total:
                time.sleep(self.config.batch_delay)

        logger.info("=" * 60)
        logger.info(f"Grading complete: {len(self.results)} traces processed")

        return self.results

    def save_results(self) -> None:
        """Save graded results to appropriate files."""

        # Create data directory if needed
        Path("./data").mkdir(exist_ok=True)

        # Save all graded results
        with open(self.config.output_file, "w") as f:
            for result in self.results:
                f.write(json.dumps(result.to_dict()) + "\n")
        logger.info(f"Saved all grades to {self.config.output_file}")

        # Save high-quality traces for training
        high_quality = [r for r in self.results if r.tier == "high_quality"]
        if high_quality:
            self._save_for_training(high_quality, self.config.training_file)
            logger.info(f"Saved {len(high_quality)} high-quality traces to {self.config.training_file}")

        # Save near-miss traces for analysis
        near_miss = [r for r in self.results if r.tier == "near_miss"]
        if near_miss:
            self._save_for_training(near_miss, self.config.nearmiss_file)
            logger.info(f"Saved {len(near_miss)} near-miss traces to {self.config.nearmiss_file}")

    def _save_for_training(self, results: list[GradeResult], path: str) -> None:
        """Convert graded results to training format and save."""
        with open(path, "w") as f:
            for r in results:
                # Convert to chat format for MLX-LM training
                training_example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": self._get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": r.prompt
                        },
                        {
                            "role": "assistant",
                            "content": r.response
                        }
                    ],
                    "metadata": {
                        "grade": r.overall_score,
                        "tier": r.tier,
                        "category": r.category
                    }
                }
                f.write(json.dumps(training_example) + "\n")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for training format."""
        return """You are a PNC Strategic Advisor. Your goal is to provide high-fidelity financial analysis. Before responding, you must perform a 'Reasoning Trace' using these steps:

1. Data Extraction: Identify the core financial facts provided in the input.
2. Regulatory Check: Cross-reference the request against standard bank policies and regulations.
3. Logical Modeling: Perform calculations or trend analysis step-by-step.
4. UI Planning: Determine which "Flash UI" components best represent this data.
5. Critique: Identify one potential risk or "hallucination point" in your own logic.

Output Format:
- Wrap your reasoning in <reasoning> tags
- Wrap your final user-facing response in <message> tags"""

    def print_summary(self) -> None:
        """Print grading summary."""
        if not self.results:
            logger.warning("No results to summarize")
            return

        # Calculate averages
        avg_accuracy = sum(r.accuracy for r in self.results) / len(self.results)
        avg_policy = sum(r.policy_compliance for r in self.results) / len(self.results)
        avg_format = sum(r.formatting for r in self.results) / len(self.results)
        avg_ui = sum(r.ui_quality for r in self.results) / len(self.results)
        avg_overall = sum(r.overall_score for r in self.results) / len(self.results)

        print("\n" + "=" * 60)
        print("GRADING SUMMARY")
        print("=" * 60)
        print(f"Total traces graded: {len(self.results)}")
        print()
        print("Tier Distribution:")
        print(f"  High Quality (8+):  {self.stats['high_quality']} "
              f"({100*self.stats['high_quality']/len(self.results):.1f}%)")
        print(f"  Near Miss (5-7):    {self.stats['near_miss']} "
              f"({100*self.stats['near_miss']/len(self.results):.1f}%)")
        print(f"  Discard (<5):       {self.stats['discard']} "
              f"({100*self.stats['discard']/len(self.results):.1f}%)")
        print()
        print("Average Scores:")
        print(f"  Accuracy:         {avg_accuracy:.2f}/10")
        print(f"  Policy Compliance:{avg_policy:.2f}/10")
        print(f"  Formatting:       {avg_format:.2f}/10")
        print(f"  UI Quality:       {avg_ui:.2f}/10")
        print(f"  Overall:          {avg_overall:.2f}/10")
        print()
        print("=" * 60)

        # Category breakdown
        by_category = {}
        for r in self.results:
            cat = r.category
            if cat not in by_category:
                by_category[cat] = {"count": 0, "score_sum": 0}
            by_category[cat]["count"] += 1
            by_category[cat]["score_sum"] += r.overall_score

        print("\nBy Category:")
        for cat, data in sorted(by_category.items()):
            avg = data["score_sum"] / data["count"]
            print(f"  {cat}: {data['count']} traces, avg {avg:.1f}/10")

        print("\n" + "=" * 60)
        print("OUTPUT FILES")
        print("=" * 60)
        print(f"  All grades:    {self.config.output_file}")
        print(f"  High quality:  {self.config.training_file}")
        print(f"  Near miss:     {self.config.nearmiss_file}")
        print()
        print("NEXT STEPS:")
        if self.stats['high_quality'] > 0:
            print(f"  1. Add {self.stats['high_quality']} high-quality traces to training data")
            print("  2. Run: python flywheel.py --retrain")
        else:
            print("  No high-quality traces found. Review near-miss traces for improvement.")
        print("=" * 60 + "\n")


# =============================================================================
# Main Entry Point
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grade S1 reasoning traces using Claude API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Grade all traces
    python grade_with_claude.py --traces s1_traces.jsonl

    # Grade first 5 traces (testing)
    python grade_with_claude.py --traces s1_traces.jsonl --limit 5

    # Custom output file
    python grade_with_claude.py --traces s1_traces.jsonl --output my_grades.jsonl

    # Use different Claude model
    python grade_with_claude.py --traces s1_traces.jsonl --model claude-opus-4-20250514
        """
    )

    BACKEND_DIR = Path(__file__).parent.absolute()
    PROJECT_ROOT = BACKEND_DIR.parent.parent
    DATA_DIR = PROJECT_ROOT / "data" / "training"

    parser.add_argument(
        "--traces", "-t",
        default=str(DATA_DIR / "s1_traces.jsonl"),
        help="Path to S1 traces JSONL file"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(DATA_DIR / "graded_traces.jsonl"),
        help="Path to output graded traces JSONL file"
    )
    parser.add_argument(
        "--model", "-m",
        default="claude-sonnet-4-20250514",
        help="Claude model to use for grading"
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        help="Limit number of traces to grade"
    )
    parser.add_argument(
        "--skip", "-s",
        type=int,
        default=0,
        help="Skip first N traces"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API calls (seconds)"
    )

    args = parser.parse_args()

    # Check for API key early
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        print("\nGet your API key from: https://console.anthropic.com/")
        return 1

    # Build config
    config = GraderConfig(
        traces_file=args.traces,
        output_file=args.output,
        model=args.model,
        limit=args.limit,
        skip=args.skip,
        batch_delay=args.delay,
    )

    # Run grading pipeline
    pipeline = GradingPipeline(config)
    pipeline.grade_all()
    pipeline.save_results()
    pipeline.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
