#!/usr/bin/env python3
"""
PNC Strategic Foundry - Defense-in-Depth PII Anonymization Orchestrator
=======================================================================

This module implements a multi-layered PII scrubbing pipeline designed for
the PNC Strategic Foundry's AI Flywheel architecture.

Architecture:
    Layer 1 (Deterministic): Regex-based detection for fixed patterns
    Layer 2 (Structural):    Microsoft Presidio NER for standard entities
    Layer 3 (Cognitive):     Fine-tuned Qwen 2.5 3B for context-aware scrubbing

Requirements:
    - Python 3.10+
    - mlx-lm (Apple Silicon optimized)
    - presidio-analyzer
    - presidio-anonymizer
    - spacy with en_core_web_lg model

Installation:
    pip install mlx-lm presidio-analyzer presidio-anonymizer spacy
    python -m spacy download en_core_web_lg

Author: PNC Strategic Foundry Engineering Team
Version: 1.0.0
"""

from __future__ import annotations

import logging
import re
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

# Configure logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PNC.Anonymizer")


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class AnonymizerConfig:
    """Configuration for the PII Anonymization pipeline."""

    # Model Configuration
    base_model: str = "Qwen/Qwen2.5-3B-Instruct"
    adapter_path: str = str(Path(__file__).parent / "pnc_scrubber_adapter")

    # Layer toggles (for debugging/testing)
    enable_layer1_regex: bool = True
    enable_layer2_presidio: bool = True
    enable_layer3_cognitive: bool = True

    # Cognitive Layer Settings
    max_tokens: int = 512
    temperature: float = 0.1  # Low temp for deterministic output
    top_p: float = 0.95

    # Presidio Settings
    presidio_language: str = "en"
    presidio_score_threshold: float = 0.5

    # Performance Settings
    log_timing: bool = True
    verbose: bool = False


# =============================================================================
# PII Placeholder Definitions
# =============================================================================

class PIIPlaceholder(Enum):
    """Standard PII placeholders as defined in the project schema."""

    CUSTOMER_IDENTIFIER = "<CUSTOMER_IDENTIFIER>"
    FINANCIAL_ID = "<FINANCIAL_ID>"
    LOCATION_SENSITIVE = "<LOCATION_SENSITIVE>"
    SENSITIVE_CONTEXT = "<SENSITIVE_CONTEXT>"
    CURRENCY_VALUE = "<CURRENCY_VALUE>"
    SSN = "<SSN_REDACTED>"
    ACCOUNT_NUMBER = "<ACCOUNT_REDACTED>"
    ROUTING_NUMBER = "<ROUTING_REDACTED>"
    PHONE_NUMBER = "<PHONE_REDACTED>"
    EMAIL = "<EMAIL_REDACTED>"
    DATE_OF_BIRTH = "<DOB_REDACTED>"


# =============================================================================
# Layer 1: Deterministic Regex-Based Detection
# =============================================================================

@dataclass
class RegexPattern:
    """Defines a regex pattern for PII detection."""

    name: str
    pattern: re.Pattern
    placeholder: str
    priority: int = 0  # Higher priority patterns are applied first


class Layer1RegexScrubber:
    """
    Layer 1: Deterministic PII detection using regex patterns.

    This layer provides 100% accuracy for fixed-format PII:
    - Social Security Numbers (SSN)
    - Account Numbers
    - Routing Numbers
    - Phone Numbers
    - Email Addresses
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("PNC.Anonymizer.Layer1")
        self.patterns = self._compile_patterns()
        self.logger.info(f"Initialized with {len(self.patterns)} regex patterns")

    def _compile_patterns(self) -> list[RegexPattern]:
        """Compile all regex patterns for PII detection."""

        patterns = [
            # SSN: xxx-xx-xxxx or xxxxxxxxx
            RegexPattern(
                name="SSN",
                pattern=re.compile(
                    r"\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b"
                ),
                placeholder=PIIPlaceholder.SSN.value,
                priority=100,
            ),
            # Account Numbers: Various formats (4-17 digits, may have dashes)
            RegexPattern(
                name="Account_Number_Suffix",
                pattern=re.compile(
                    r"\b(?:account|acct|acc)[\s#:]*(?:ending|ends|number|no|#)?[\s:]*"
                    r"(?:in\s+)?(\d{2,4}[-\s]?\d{2,4}(?:[-\s]?\d{2,4})?)\b",
                    re.IGNORECASE,
                ),
                placeholder=PIIPlaceholder.ACCOUNT_NUMBER.value,
                priority=90,
            ),
            # Standalone account-like numbers (4+ digits with optional separators)
            RegexPattern(
                name="Account_Number_Standalone",
                pattern=re.compile(
                    r"\b\d{4,6}[-\s]?\d{4}(?:[-\s]?\d{2,4})?\b"
                ),
                placeholder=PIIPlaceholder.FINANCIAL_ID.value,
                priority=50,
            ),
            # Routing Numbers: 9 digits (ABA format)
            RegexPattern(
                name="Routing_Number",
                pattern=re.compile(
                    r"\b(?:routing|aba|transit)[\s#:]*(?:number|no|#)?[\s:]*"
                    r"(\d{9})\b",
                    re.IGNORECASE,
                ),
                placeholder=PIIPlaceholder.ROUTING_NUMBER.value,
                priority=95,
            ),
            # Phone Numbers: Various US formats
            RegexPattern(
                name="Phone_Number",
                pattern=re.compile(
                    r"\b(?:\+1[-.\s]?)?"
                    r"(?:\(?[2-9]\d{2}\)?[-.\s]?)"
                    r"[2-9]\d{2}[-.\s]?\d{4}\b"
                ),
                placeholder=PIIPlaceholder.PHONE_NUMBER.value,
                priority=80,
            ),
            # Email Addresses
            RegexPattern(
                name="Email",
                pattern=re.compile(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                ),
                placeholder=PIIPlaceholder.EMAIL.value,
                priority=85,
            ),
            # Currency Values: $X,XXX.XX format
            RegexPattern(
                name="Currency",
                pattern=re.compile(
                    r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?"
                    r"(?:\s?(?:M|MM|B|K|million|billion|thousand))?\b",
                    re.IGNORECASE,
                ),
                placeholder=PIIPlaceholder.CURRENCY_VALUE.value,
                priority=70,
            ),
            # Date of Birth patterns
            RegexPattern(
                name="DOB",
                pattern=re.compile(
                    r"\b(?:dob|date\s+of\s+birth|born|birthday)[\s:]*"
                    r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
                    re.IGNORECASE,
                ),
                placeholder=PIIPlaceholder.DATE_OF_BIRTH.value,
                priority=75,
            ),
        ]

        # Sort by priority (highest first)
        return sorted(patterns, key=lambda p: p.priority, reverse=True)

    def scrub(self, text: str) -> tuple[str, dict[str, int]]:
        """
        Apply regex-based PII scrubbing to input text.

        Args:
            text: Input text to scrub

        Returns:
            Tuple of (scrubbed_text, detection_counts)
        """
        detection_counts: dict[str, int] = {}
        scrubbed = text

        for pattern in self.patterns:
            matches = list(pattern.pattern.finditer(scrubbed))
            if matches:
                detection_counts[pattern.name] = len(matches)
                scrubbed = pattern.pattern.sub(pattern.placeholder, scrubbed)
                self.logger.debug(
                    f"Pattern '{pattern.name}' matched {len(matches)} time(s)"
                )

        total_detections = sum(detection_counts.values())
        if total_detections > 0:
            self.logger.info(f"Layer 1 detected {total_detections} PII instances")

        return scrubbed, detection_counts


# =============================================================================
# Layer 2: Microsoft Presidio NER-Based Detection
# =============================================================================

class Layer2PresidioScrubber:
    """
    Layer 2: Structural PII detection using Microsoft Presidio.

    Handles standard named entity recognition:
    - Person Names
    - Locations/Addresses
    - Organizations
    - Dates
    """

    def __init__(self, config: AnonymizerConfig) -> None:
        self.logger = logging.getLogger("PNC.Anonymizer.Layer2")
        self.config = config
        self.analyzer = None
        self.anonymizer = None
        self._initialize_presidio()

    def _initialize_presidio(self) -> None:
        """Initialize Presidio analyzer and anonymizer engines."""
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            from presidio_anonymizer.entities import OperatorConfig

            self.logger.info("Initializing Presidio engines...")

            # Initialize analyzer with spaCy NLP engine
            self.analyzer = AnalyzerEngine()

            # Initialize anonymizer
            self.anonymizer = AnonymizerEngine()

            # Define entity-to-placeholder mapping
            self.entity_mapping = {
                "PERSON": PIIPlaceholder.CUSTOMER_IDENTIFIER.value,
                "LOCATION": PIIPlaceholder.LOCATION_SENSITIVE.value,
                "GPE": PIIPlaceholder.LOCATION_SENSITIVE.value,  # Geo-political entity
                "ORG": PIIPlaceholder.SENSITIVE_CONTEXT.value,
                "DATE_TIME": PIIPlaceholder.SENSITIVE_CONTEXT.value,
                "NRP": PIIPlaceholder.SENSITIVE_CONTEXT.value,  # Nationality/Religion/Political
                "EMAIL_ADDRESS": PIIPlaceholder.EMAIL.value,
                "PHONE_NUMBER": PIIPlaceholder.PHONE_NUMBER.value,
                "US_SSN": PIIPlaceholder.SSN.value,
                "US_BANK_NUMBER": PIIPlaceholder.FINANCIAL_ID.value,
                "CREDIT_CARD": PIIPlaceholder.FINANCIAL_ID.value,
                "IBAN_CODE": PIIPlaceholder.FINANCIAL_ID.value,
            }

            self.logger.info("Presidio engines initialized successfully")

        except ImportError as e:
            self.logger.warning(
                f"Presidio not available: {e}. Layer 2 will be skipped."
            )
            self.analyzer = None
            self.anonymizer = None

        except Exception as e:
            self.logger.error(f"Failed to initialize Presidio: {e}")
            self.analyzer = None
            self.anonymizer = None

    def scrub(self, text: str) -> tuple[str, dict[str, int]]:
        """
        Apply Presidio NER-based PII scrubbing.

        Args:
            text: Input text to scrub

        Returns:
            Tuple of (scrubbed_text, detection_counts)
        """
        if self.analyzer is None or self.anonymizer is None:
            self.logger.warning("Presidio not initialized, skipping Layer 2")
            return text, {}

        try:
            from presidio_anonymizer.entities import OperatorConfig

            # Analyze text for PII entities
            results = self.analyzer.analyze(
                text=text,
                language=self.config.presidio_language,
                score_threshold=self.config.presidio_score_threshold,
            )

            if not results:
                self.logger.debug("No entities detected by Presidio")
                return text, {}

            # Count detections by entity type
            detection_counts: dict[str, int] = {}
            for result in results:
                entity_type = result.entity_type
                detection_counts[entity_type] = detection_counts.get(entity_type, 0) + 1

            # Build operator configuration for anonymization
            operators = {}
            for entity_type in detection_counts.keys():
                placeholder = self.entity_mapping.get(
                    entity_type, PIIPlaceholder.SENSITIVE_CONTEXT.value
                )
                operators[entity_type] = OperatorConfig(
                    "replace", {"new_value": placeholder}
                )

            # Anonymize the text
            anonymized_result = self.anonymizer.anonymize(
                text=text, analyzer_results=results, operators=operators
            )

            total_detections = sum(detection_counts.values())
            self.logger.info(f"Layer 2 detected {total_detections} entities")

            return anonymized_result.text, detection_counts

        except Exception as e:
            self.logger.error(f"Presidio scrubbing failed: {e}")
            return text, {}


# =============================================================================
# Layer 3: Cognitive MLX-LM Based Detection
# =============================================================================

class Layer3CognitiveScrubber:
    """
    Layer 3: Context-aware PII scrubbing using fine-tuned Qwen 2.5 3B.

    This layer catches subtle, context-dependent PII that regex and NER miss:
    - Unique job titles that identify individuals
    - Specific events that could fingerprint clients
    - Business descriptions with identifying details
    - Rare circumstances or combinations
    """

    SYSTEM_PROMPT = """Execute Layer 3 Cognitive Scrubbing: Identify and replace subtle PII and context-heavy identifiers while maintaining financial intent.

You are the final layer in a PII anonymization pipeline. Previous layers have already handled obvious PII like names, SSNs, and account numbers. Your job is to identify and scrub CONTEXT-DEPENDENT PII that could still identify someone:

1. Unique job titles (e.g., "head of neurosurgery at UPMC" -> "<SENSITIVE_CONTEXT>")
2. Identifying events (e.g., "won the lottery last February" -> "<SENSITIVE_CONTEXT>")
3. Unique business descriptions (e.g., "the only halal slaughterhouse in western PA" -> "<BUSINESS_TYPE> in <LOCATION_SENSITIVE>")
4. Specific asset details (e.g., "1952 Ferrari 225 Sport" -> "<SENSITIVE_CONTEXT>")
5. Family/relationship identifiers combined with other details

Preserve all financial intent and structure. Only replace identifying context with appropriate placeholders:
- <CUSTOMER_IDENTIFIER>: Names, aliases
- <FINANCIAL_ID>: Account suffixes, loan IDs
- <LOCATION_SENSITIVE>: Addresses, unique locations
- <SENSITIVE_CONTEXT>: Unique titles, events, details
- <CURRENCY_VALUE>: Monetary amounts
- <BUSINESS_TYPE>: Type of business"""

    def __init__(self, config: AnonymizerConfig) -> None:
        self.logger = logging.getLogger("PNC.Anonymizer.Layer3")
        self.config = config
        self.model = None
        self.tokenizer = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the MLX-LM model with fine-tuned adapter."""
        try:
            from mlx_lm import load

            adapter_path = Path(self.config.adapter_path)

            # Check if adapter exists
            if not adapter_path.exists():
                self.logger.warning(
                    f"Adapter not found at {adapter_path}. "
                    "Layer 3 will use base model without fine-tuning. "
                    "Run train_mlx.sh to create the adapter."
                )
                # Load base model without adapter
                self.logger.info(f"Loading base model: {self.config.base_model}")
                self.model, self.tokenizer = load(self.config.base_model)
            else:
                # Load model with adapter
                self.logger.info(
                    f"Loading model {self.config.base_model} "
                    f"with adapter from {adapter_path}"
                )
                self.model, self.tokenizer = load(
                    self.config.base_model, adapter_path=str(adapter_path)
                )

            self.logger.info("Cognitive layer model loaded successfully")

        except ImportError as e:
            self.logger.error(
                f"mlx_lm not available: {e}. "
                "Install with: pip install mlx-lm"
            )
            self.model = None
            self.tokenizer = None

        except Exception as e:
            self.logger.error(f"Failed to load cognitive model: {e}")
            self.model = None
            self.tokenizer = None

    def scrub(self, text: str) -> tuple[str, bool]:
        """
        Apply cognitive context-aware PII scrubbing.

        Args:
            text: Input text to scrub (already processed by Layers 1 & 2)

        Returns:
            Tuple of (scrubbed_text, was_modified)
        """
        if self.model is None or self.tokenizer is None:
            self.logger.warning("Cognitive model not loaded, skipping Layer 3")
            return text, False

        try:
            from mlx_lm import generate

            # Build chat messages
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ]

            # Apply chat template
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            # Generate response
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=self.config.max_tokens,
                temp=self.config.temperature,
                top_p=self.config.top_p,
                verbose=self.config.verbose,
            )

            # Clean up response (remove any chat template artifacts)
            scrubbed = self._clean_response(response, text)

            # Check if modifications were made
            was_modified = scrubbed != text

            if was_modified:
                self.logger.info("Layer 3 applied context-aware modifications")
            else:
                self.logger.debug("Layer 3 found no additional PII to scrub")

            return scrubbed, was_modified

        except Exception as e:
            self.logger.error(f"Cognitive scrubbing failed: {e}")
            return text, False

    def _clean_response(self, response: str, original: str) -> str:
        """Clean the model response and handle edge cases."""
        # Strip whitespace
        cleaned = response.strip()

        # If response is empty or much shorter, return original
        if len(cleaned) < len(original) * 0.3:
            self.logger.warning("Model response too short, keeping original")
            return original

        # If response is much longer (model hallucinated), return original
        if len(cleaned) > len(original) * 2:
            self.logger.warning("Model response too long, keeping original")
            return original

        return cleaned


# =============================================================================
# Main Orchestrator
# =============================================================================

@dataclass
class ScrubResult:
    """Result of a complete PII scrubbing operation."""

    original_text: str
    scrubbed_text: str
    layer1_detections: dict[str, int] = field(default_factory=dict)
    layer2_detections: dict[str, int] = field(default_factory=dict)
    layer3_modified: bool = False
    total_time_ms: float = 0.0
    layer_times_ms: dict[str, float] = field(default_factory=dict)

    @property
    def total_detections(self) -> int:
        """Total number of PII detections across all layers."""
        return (
            sum(self.layer1_detections.values())
            + sum(self.layer2_detections.values())
            + (1 if self.layer3_modified else 0)
        )

    @property
    def was_modified(self) -> bool:
        """Whether the text was modified by any layer."""
        return self.original_text != self.scrubbed_text

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "original_text": self.original_text,
            "scrubbed_text": self.scrubbed_text,
            "layer1_detections": self.layer1_detections,
            "layer2_detections": self.layer2_detections,
            "layer3_modified": self.layer3_modified,
            "total_detections": self.total_detections,
            "was_modified": self.was_modified,
            "total_time_ms": round(self.total_time_ms, 2),
            "layer_times_ms": {k: round(v, 2) for k, v in self.layer_times_ms.items()},
        }


class PIIAnonymizer:
    """
    Main orchestrator for the Defense-in-Depth PII Anonymization pipeline.

    Usage:
        anonymizer = PIIAnonymizer()
        result = anonymizer.scrub("John Smith, SSN 123-45-6789, account 4421")
        print(result.scrubbed_text)
    """

    def __init__(self, config: Optional[AnonymizerConfig] = None) -> None:
        """
        Initialize the PII Anonymizer with all three layers.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.logger = logging.getLogger("PNC.Anonymizer")
        self.config = config or AnonymizerConfig()

        self.logger.info("=" * 60)
        self.logger.info("PNC Strategic Foundry - PII Anonymizer Initializing")
        self.logger.info("=" * 60)

        # Initialize layers
        self._init_layers()

        self.logger.info("PII Anonymizer ready")
        self.logger.info("=" * 60)

    def _init_layers(self) -> None:
        """Initialize all scrubbing layers."""
        self.layer1: Optional[Layer1RegexScrubber] = None
        self.layer2: Optional[Layer2PresidioScrubber] = None
        self.layer3: Optional[Layer3CognitiveScrubber] = None

        if self.config.enable_layer1_regex:
            self.logger.info("Initializing Layer 1 (Regex)...")
            self.layer1 = Layer1RegexScrubber()

        if self.config.enable_layer2_presidio:
            self.logger.info("Initializing Layer 2 (Presidio)...")
            self.layer2 = Layer2PresidioScrubber(self.config)

        if self.config.enable_layer3_cognitive:
            self.logger.info("Initializing Layer 3 (Cognitive)...")
            self.layer3 = Layer3CognitiveScrubber(self.config)

    def scrub(self, text: str) -> ScrubResult:
        """
        Run the complete Defense-in-Depth PII scrubbing pipeline.

        Args:
            text: Input text to anonymize

        Returns:
            ScrubResult with scrubbed text and metadata
        """
        start_time = time.perf_counter()
        layer_times: dict[str, float] = {}

        result = ScrubResult(original_text=text, scrubbed_text=text)
        current_text = text

        # Layer 1: Regex
        if self.layer1:
            layer_start = time.perf_counter()
            current_text, detections = self.layer1.scrub(current_text)
            result.layer1_detections = detections
            layer_times["layer1_regex"] = (time.perf_counter() - layer_start) * 1000

        # Layer 2: Presidio
        if self.layer2:
            layer_start = time.perf_counter()
            current_text, detections = self.layer2.scrub(current_text)
            result.layer2_detections = detections
            layer_times["layer2_presidio"] = (time.perf_counter() - layer_start) * 1000

        # Layer 3: Cognitive
        if self.layer3:
            layer_start = time.perf_counter()
            current_text, modified = self.layer3.scrub(current_text)
            result.layer3_modified = modified
            layer_times["layer3_cognitive"] = (time.perf_counter() - layer_start) * 1000

        result.scrubbed_text = current_text
        result.total_time_ms = (time.perf_counter() - start_time) * 1000
        result.layer_times_ms = layer_times

        if self.config.log_timing:
            self.logger.info(
                f"Scrubbing completed in {result.total_time_ms:.2f}ms "
                f"(L1: {layer_times.get('layer1_regex', 0):.2f}ms, "
                f"L2: {layer_times.get('layer2_presidio', 0):.2f}ms, "
                f"L3: {layer_times.get('layer3_cognitive', 0):.2f}ms)"
            )

        return result

    def scrub_batch(
        self, texts: list[str], callback: Optional[Callable[[int, int], None]] = None
    ) -> list[ScrubResult]:
        """
        Scrub a batch of texts.

        Args:
            texts: List of texts to anonymize
            callback: Optional progress callback(current, total)

        Returns:
            List of ScrubResult objects
        """
        results = []
        total = len(texts)

        for i, text in enumerate(texts):
            result = self.scrub(text)
            results.append(result)

            if callback:
                callback(i + 1, total)

        return results


# =============================================================================
# CLI Interface
# =============================================================================

def main() -> int:
    """Main entry point for CLI usage."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="PNC Strategic Foundry - PII Anonymization Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scrub a single text string
    python orchestrator.py --text "John Smith at 123 Main St, SSN 123-45-6789"

    # Scrub from a file
    python orchestrator.py --file input.txt --output scrubbed.txt

    # Scrub JSONL file (for batch processing)
    python orchestrator.py --jsonl input.jsonl --output-jsonl scrubbed.jsonl

    # Disable specific layers for testing
    python orchestrator.py --text "test" --no-layer3
        """,
    )

    parser.add_argument("--text", "-t", help="Text to anonymize")
    parser.add_argument("--file", "-f", help="Input file to anonymize")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--jsonl", help="Input JSONL file for batch processing")
    parser.add_argument("--output-jsonl", help="Output JSONL file for batch results")

    parser.add_argument(
        "--no-layer1", action="store_true", help="Disable Layer 1 (Regex)"
    )
    parser.add_argument(
        "--no-layer2", action="store_true", help="Disable Layer 2 (Presidio)"
    )
    parser.add_argument(
        "--no-layer3", action="store_true", help="Disable Layer 3 (Cognitive)"
    )

    parser.add_argument(
        "--adapter", default="./pnc_scrubber_adapter", help="Path to LoRA adapter"
    )
    parser.add_argument(
        "--model", default="Qwen/Qwen2.5-3B-Instruct", help="Base model name"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Build configuration
    config = AnonymizerConfig(
        base_model=args.model,
        adapter_path=args.adapter,
        enable_layer1_regex=not args.no_layer1,
        enable_layer2_presidio=not args.no_layer2,
        enable_layer3_cognitive=not args.no_layer3,
        verbose=args.verbose,
    )

    # Initialize anonymizer
    anonymizer = PIIAnonymizer(config)

    # Process based on input type
    if args.text:
        result = anonymizer.scrub(args.text)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"\n{'='*60}")
            print("ORIGINAL:")
            print(result.original_text)
            print(f"\n{'='*60}")
            print("SCRUBBED:")
            print(result.scrubbed_text)
            print(f"\n{'='*60}")
            print(f"Detections: {result.total_detections}")
            print(f"Time: {result.total_time_ms:.2f}ms")

    elif args.file:
        with open(args.file, "r") as f:
            text = f.read()

        result = anonymizer.scrub(text)

        if args.output:
            with open(args.output, "w") as f:
                f.write(result.scrubbed_text)
            logger.info(f"Scrubbed output written to {args.output}")
        else:
            print(result.scrubbed_text)

    elif args.jsonl:
        results = []
        with open(args.jsonl, "r") as f:
            lines = f.readlines()

        total = len(lines)
        for i, line in enumerate(lines):
            data = json.loads(line)
            input_text = data.get("input", data.get("text", ""))

            if input_text:
                result = anonymizer.scrub(input_text)
                data["scrubbed"] = result.scrubbed_text
                data["anonymizer_metadata"] = {
                    "layer1_detections": result.layer1_detections,
                    "layer2_detections": result.layer2_detections,
                    "layer3_modified": result.layer3_modified,
                }
                results.append(data)

            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i+1}/{total} records")

        if args.output_jsonl:
            with open(args.output_jsonl, "w") as f:
                for r in results:
                    f.write(json.dumps(r) + "\n")
            logger.info(f"Batch results written to {args.output_jsonl}")

    else:
        # Interactive mode
        print("PNC Strategic Foundry - PII Anonymizer")
        print("Enter text to anonymize (Ctrl+D to exit):")
        print()

        try:
            while True:
                text = input("> ")
                if text.strip():
                    result = anonymizer.scrub(text)
                    print(f"  {result.scrubbed_text}")
                    print(f"  [{result.total_detections} detections, {result.total_time_ms:.0f}ms]")
                    print()
        except EOFError:
            print("\nExiting.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
