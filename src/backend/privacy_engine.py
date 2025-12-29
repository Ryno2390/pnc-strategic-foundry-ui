"""
PNC Strategic Foundry - K-Anonymity Privacy Scorer (GLBA Compliance)
====================================================================

Operationalizes Data Safeguards by ensuring that individuals cannot be 
uniquely identified via combinations of non-PII attributes 
(e.g., "The only CEO in Fox Chapel").

Implements the K-Anonymity principle: A record is K-anonymous if its 
quasi-identifiers are identical to at least K-1 other records in the dataset.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter

class PrivacyScorer:
    """
    Evaluates the risk of re-identification within the Unified Entity Graph.
    """

    def __init__(self, entities_path: Path):
        self.entities_path = entities_path
        self.entities = []
        self._load_data()

    def _load_data(self):
        if self.entities_path.exists():
            with open(self.entities_path, "r") as f:
                self.entities = json.load(f)

    def calculate_anonymity_score(self, quasi_identifiers: Dict[str, str]) -> int:
        """
        Given a set of attributes (e.g., {"city": "Pittsburgh", "type": "PERSON"}),
        counts how many entities share these exact attributes.
        
        Returns the 'K' value. K=1 means the person is uniquely identifiable.
        """
        if not self.entities:
            return 0
            
        count = 0
        for entity in self.entities:
            # Flatten entity for comparison
            match = True
            for key, val in quasi_identifiers.items():
                # 1. Check top level attributes
                if key in entity and str(entity[key]).upper() == str(val).upper():
                    continue
                
                # 2. Check within addresses list
                addr_match = False
                for addr in entity.get("addresses", []):
                    if key in addr and str(addr[key]).upper() == str(val).upper():
                        addr_match = True
                        break
                
                if addr_match:
                    continue
                
                match = False
                break
            
            if match:
                count += 1
                
        return count

    def get_risk_level(self, k_value: int) -> str:
        """Translates K-Anonymity value into a risk level."""
        if k_value <= 1:
            return "CRITICAL (Uniquely Identifiable)"
        if k_value < 5:
            return "HIGH (Low Anonymity)"
        if k_value < 10:
            return "MEDIUM"
        return "LOW (High Anonymity)"

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    entities_file = project_root / "data" / "relationship_store" / "resolved" / "unified_entities.json"
    
    scorer = PrivacyScorer(entities_file)
    
    # Test identifying a specific combination
    test_attributes = {"city": "FOX CHAPEL"}
    k = scorer.calculate_anonymity_score(test_attributes)
    print(f"Combination: {test_attributes}")
    print(f"K-Anonymity: {k} ({scorer.get_risk_level(k)})")
