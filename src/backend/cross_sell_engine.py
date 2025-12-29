import json
from pathlib import Path
from typing import List, Dict, Any

class CrossSellOptimizer:
    """
    Business Intelligence: Strategic Cross-Sell Optimizer.
    Scans the Unified Entity Graph to identify high-value relationship gaps.
    """

    def __init__(self, data_dir: str = "./data/relationship_store/resolved"):
        self.data_dir = Path(data_dir)
        self.entities_path = self.data_dir / "unified_entities.json"
        self.relationships_path = self.data_dir / "relationships.json"

    def analyze_opportunities(self) -> List[Dict[str, Any]]:
        if not self.entities_path.exists():
            return []

        with open(self.entities_path, "r") as f:
            entities = json.load(f)
            
        opportunities = []
        
        for entity in entities:
            if entity["entity_type"] != "PERSON":
                continue
                
            sources = [s["source"] for s in entity.get("source_records", [])]
            
            # Opportunity 1: Commercial Owner without Wealth relationship
            is_commercial = "COMMERCIAL_CORE" in sources
            is_wealth = "WEALTH_ADVISORY" in sources
            
            if is_commercial and not is_wealth:
                opportunities.append({
                    "entity_id": entity["unified_id"],
                    "name": entity["canonical_name"],
                    "opportunity": "WEALTH_ADVISORY_REFERRAL",
                    "reason": "Entity has established commercial business relationship but no wealth management presence.",
                    "priority": "HIGH"
                })
                
            # Opportunity 2: High-Net-Worth Household without 529 plan check
            # (Logic would be expanded with actual balances)
            if is_wealth and "CONSUMER_CORE" not in sources:
                opportunities.append({
                    "entity_id": entity["unified_id"],
                    "name": entity["canonical_name"],
                    "opportunity": "RETAIL_ONBOARDING",
                    "reason": "Wealth client has no personal checking/savings accounts identified.",
                    "priority": "MEDIUM"
                })

        return opportunities

if __name__ == "__main__":
    optimizer = CrossSellOptimizer()
    opps = optimizer.analyze_opportunities()
    print(f"--- Found {len(opps)} Cross-Sell Opportunities ---")
    for o in opps[:5]:
        print(f"[{o['priority']}] {o['name']}: {o['opportunity']}")
        print(f"Reason: {o['reason']}\n")
