"""
PNC Strategic Foundry - Adverse Action Reasoner (Reg B Compliance)
==================================================================

Operationalizes the Equal Credit Opportunity Act (Reg B) by ensuring that 
any AI-driven credit denial is accompanied by specific, legally compliant 
reasons derived from deterministic data.
"""

import json
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

class ECOAReason(Enum):
    INSUFFICIENT_INCOME = "Income insufficient for amount of credit requested"
    HIGH_DTI = "Excess obligations in relation to income"
    LOW_DSCR = "Insufficient cash flow to service debt"
    INSUFFICIENT_CREDIT_HISTORY = "Insufficient length of credit history"
    LOW_CREDIT_SCORE = "Credit score below minimum requirements"
    INSUFFICIENT_COLLATERAL = "Value or type of collateral not sufficient"
    DELINQUENT_OBLIGATIONS = "Delinquent past or present credit obligations with others"
    INCOMPLETE_APPLICATION = "Incomplete application"

@dataclass
class AdverseActionNotice:
    notice_id: str
    timestamp: str
    entity_name: str
    action_taken: str = "DENIED"
    principal_reasons: List[str] = None
    metrics_cited: Dict[str, Any] = None
    disclosure_text: str = "The Federal Equal Credit Opportunity Act prohibits creditors from discriminating against applicants on the basis of race, color, religion, national origin, sex, marital status, age (provided the applicant has the capacity to enter into a binding contract)..."

class AdverseActionReasoner:
    """
    Translates failed financial guardrails into compliant Adverse Action Notices.
    """

    def __init__(self):
        pass

    def generate_notice(self, entity_name: str, guardrail_results: Dict[str, Any]) -> AdverseActionNotice:
        """
        Takes the output of FinancialGuardrails and maps failures to ECOA reasons.
        """
        reasons = []
        metrics = {}
        
        checks = guardrail_results.get("checks", {})
        actual_metrics = guardrail_results.get("metrics", {})

        # Map Guardrail failures to ECOA Reasons
        if not checks.get("dscr_requirement", True):
            reasons.append(ECOAReason.LOW_DSCR.value)
            metrics["DSCR"] = actual_metrics.get("dscr")
            
        if not checks.get("credit_score", True):
            reasons.append(ECOAReason.LOW_CREDIT_SCORE.value)
            
        if not checks.get("size_standard", True):
            reasons.append("Business size exceeds maximum standards for requested program")
            metrics["Revenue"] = actual_metrics.get("revenue")

        if not reasons:
            reasons.append("Does not meet specific program requirements")

        notice = AdverseActionNotice(
            notice_id=f"AA-{datetime.now().strftime('%Y%m%d')}-{abs(hash(entity_name)) % 10000:03d}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            entity_name=entity_name,
            principal_reasons=reasons,
            metrics_cited=metrics
        )
        
        return notice

if __name__ == "__main__":
    # Simple self-test
    reasoner = AdverseActionReasoner()
    res = {"checks": {"dscr_requirement": False}, "metrics": {"dscr": 0.8}}
    notice = reasoner.generate_notice("Test Corp", res)
    print(json.dumps(asdict(notice), indent=2))
