#!/usr/bin/env python3
"""
PNC Strategic Foundry - PII Anonymization Precision/Recall Evaluator
===================================================================

Calculates precision and recall for the multi-layered PII scrubbing pipeline.
Identifies "Hallucinations" (False Positives) and "Misses" (False Negatives).
"""

import json
import sys
import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backend.orchestrator import PIIAnonymizer, AnonymizerConfig, PIIPlaceholder

@dataclass
class PIIEvalMetric:
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    tp: int = 0
    fp: int = 0
    fn: int = 0

class PIIEvaluator:
    def __init__(self, config: AnonymizerConfig = None):
        self.anonymizer = PIIAnonymizer(config)
        self.placeholders = [p.value for p in PIIPlaceholder]

    def run_eval(self, test_set_path: Path):
        print(f"Running PII Evaluation on {test_set_path.name}...")
        
        results = []
        total_tp = 0
        total_fp = 0
        total_fn = 0

        with open(test_set_path, "r") as f:
            for line in f:
                case = json.loads(line)
                text = case["text"]
                expected_pii = case["pii"] # List of {"text": "...", "type": "..."}

                # Run anonymizer
                scrub_result = self.anonymizer.scrub(text)
                scrubbed_text = scrub_result.scrubbed_text

                # Evaluate
                # We check if each expected PII was replaced by a placeholder
                # This is an approximation since we don't know exactly which placeholder replaced what
                tp = 0
                fn = 0
                for item in expected_pii:
                    if item["text"] not in scrubbed_text:
                        tp += 1
                    else:
                        fn += 1
                        print(f"  [MISS] Found '{item['text']}' in scrubbed output: {scrubbed_text}")

                # Detect False Positives (Hallucinations)
                # We check if placeholders appear where they shouldn't
                # For simplicity, if number of placeholders > number of expected PII, count as FP
                # This is rough but gives an idea of "over-scrubbing"
                placeholders_found = sum(scrubbed_text.count(p) for p in self.placeholders)
                fp = max(0, placeholders_found - len(expected_pii))
                
                if fp > 0:
                    print(f"  [HALLUCINATION] Over-scrubbed: {scrubbed_text}")

                total_tp += tp
                total_fp += fp
                total_fn += fn

        # Calculate metrics
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        print("\n" + "="*60)
        print("PII ANONYMIZATION PERFORMANCE")
        print("="*60)
        print(f"True Positives (Correctly Scrubbed):  {total_tp}")
        print(f"False Positives (Over-scrubbed):     {total_fp}")
        print(f"False Negatives (Missed PII):         {total_fn}")
        print("-"*60)
        print(f"PRECISION: {precision:.2%}")
        print(f"RECALL:    {recall:.2%}")
        print(f"F1-SCORE:  {f1:.2%}")
        print("="*60)

        return PIIEvalMetric(precision, recall, f1, total_tp, total_fp, total_fn)

def main():
    test_set = Path(__file__).parent / "data" / "pii_test_set.jsonl"
    
    # Run with default config (all layers)
    print("\n--- Testing Full Pipeline (Layers 1+2+3) ---")
    evaluator = PIIEvaluator()
    evaluator.run_eval(test_set)

    # Run without Layer 3 (Cognitive) to see the difference
    print("\n--- Testing Deterministic Only (Layers 1+2) ---")
    config_l12 = AnonymizerConfig(enable_layer3_cognitive=False)
    evaluator_l12 = PIIEvaluator(config_l12)
    evaluator_l12.run_eval(test_set)

if __name__ == "__main__":
    main()
