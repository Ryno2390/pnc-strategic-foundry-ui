import json
from pathlib import Path
from src.backend.policy_engine import PolicyEngine
from src.backend.relationship_engine.guardrails import FinancialGuardrails
from src.backend.audit_vault import AuditVault

def test_knowledge_safety():
    print("=== Testing Knowledge & Safety Engines ===")
    project_root = Path(__file__).parent.parent.parent.parent
    
    # 1. Policy Engine
    print("\n1. Touching Policy Engine...")
    pe = PolicyEngine(persist_dir=str(project_root / "data" / "policy_index"))
    pe.add_policy_files(project_root / "data" / "policies")
    query = "mortgage requirements"
    results = pe.search(query, top_k=1)
    print(f"   Query: {query}")
    if results:
        print(f"   Found: {results[0]['title']} (Score: {results[0]['score']})")
    assert len(results) > 0
    
    # 2. Financial Guardrails
    print("\n2. Touching Financial Guardrails...")
    gf = FinancialGuardrails()
    biz_data = {
        "annual_revenue": 1000000,
        "net_income": 200000,
        "annual_debt_service": 100000,
        "personal_credit_score": 750,
        "is_for_profit": True
    }
    result = gf.verify_sba_eligibility(biz_data)
    print(f"   SBA Eligibility: {result['eligible']} (DSCR: {result['metrics']['dscr']})")
    assert result['eligible'] == True
    
    # 3. Audit Vault
    print("\n3. Touching Audit Vault...")
    av = AuditVault(storage_path=str(project_root / "data" / "audit_log_test.jsonl"))
    # Clear test log
    if av.storage_path.exists():
        av.storage_path.unlink()
    
    trace = [{"step": 1, "thought": "Testing audit vault"}]
    hash_v = av.log_event("ADVISOR-001", "Test Query", trace, "Test Response")
    print(f"   Event Logged. Hash: {hash_v[:8]}")
    
    verify = av.verify_integrity()
    print(f"   Vault Integrity: {verify['status']} (Valid: {verify['valid']})")
    assert verify['valid'] == True

if __name__ == "__main__":
    test_knowledge_safety()
