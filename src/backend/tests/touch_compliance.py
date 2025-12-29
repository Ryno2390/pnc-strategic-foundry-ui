import json
from pathlib import Path
from src.backend.relationship_engine.fairness_monitor import FairnessMonitor
from src.backend.privacy_engine import PrivacyScorer
from src.backend.relationship_engine.adverse_action import AdverseActionReasoner
from src.backend.relationship_engine.guardrails import FinancialGuardrails

def test_compliance_engines():
    print("=== Testing Compliance Engines ===")
    project_root = Path(__file__).parent.parent.parent.parent
    
    # 1. Fairness Monitor
    print("\n1. Touching Fairness Monitor...")
    fm = FairnessMonitor()
    biased_text = "The applicant's race and zip code 15213 were considered."
    flagged, factors = fm.scan_trace(biased_text)
    print(f"   Input: {biased_text}")
    print(f"   Flagged: {flagged}, Factors: {factors}")
    assert flagged == True
    assert "race" in factors
    assert "zip code" in factors
    
    # 2. Privacy Scorer
    print("\n2. Touching Privacy Scorer...")
    entities_file = project_root / "data" / "relationship_store" / "resolved" / "unified_entities.json"
    ps = PrivacyScorer(entities_file)
    # Check for a city that exists in synthetic data
    test_attr = {"city": "PITTSBURGH"}
    k = ps.calculate_anonymity_score(test_attr)
    risk = ps.get_risk_level(k)
    print(f"   Attributes: {test_attr}")
    print(f"   K-Anonymity: {k}, Risk: {risk}")
    
    # 3. Adverse Action Reasoner
    print("\n3. Touching Adverse Action Reasoner...")
    aar = AdverseActionReasoner()
    gf = FinancialGuardrails()
    fail_data = {
        "annual_revenue": 10000000, # Too big
        "net_income": 50000,
        "annual_debt_service": 100000, # DSCR 0.5
        "personal_credit_score": 600,
        "is_for_profit": True
    }
    g_result = gf.verify_sba_eligibility(fail_data)
    notice = aar.generate_notice("Synthetic Corp", g_result)
    print(f"   Resulting Notice ID: {notice.notice_id}")
    print(f"   Reasons: {notice.principal_reasons}")
    assert len(notice.principal_reasons) >= 3

if __name__ == "__main__":
    test_compliance_engines()
