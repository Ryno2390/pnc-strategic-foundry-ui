import json
from pathlib import Path
from src.backend.relationship_engine.context_assembler import ContextAssembler, Entitlement
from fastapi.testclient import TestClient
from src.backend.app import app

def test_integration():
    print("=== Testing Integration Layer ===")
    
    # 1. Context Assembler
    print("\n1. Touching Context Assembler...")
    assembler = ContextAssembler()
    # Find a customer from unified entities
    project_root = Path(__file__).parent.parent.parent.parent
    entities_file = project_root / "data" / "relationship_store" / "resolved" / "unified_entities.json"
    with open(entities_file, "r") as f:
        entities = json.load(f)
    
    if entities:
        test_customer = entities[0]["canonical_name"]
        print(f"   Querying 360 for: {test_customer}")
        
        # Test entitlement filtering
        res_retail = assembler.get_customer_360(test_customer, entitlements=[Entitlement.RETAIL])
        print(f"   Entitlements applied: {res_retail.get('entitlements_applied')}")
        assert "RETAIL" in res_retail.get('entitlements_applied')
    
    # 2. FastAPI Hub
    print("\n2. Touching FastAPI Hub (Endpoints)...")
    client = TestClient(app)
    
    # Test Policy Search
    resp = client.get("/api/v1/policy/search?q=mortgage")
    print(f"   Policy Search status: {resp.status_code}")
    assert resp.status_code == 200
    assert resp.json()["status"] == True
    
    # Test Cross-Sell
    resp = client.get("/api/v1/business/opportunities")
    print(f"   Business Opps status: {resp.status_code}")
    assert resp.status_code == 200
    
    # Test Audit Integrity
    resp = client.get("/api/v1/audit/verify")
    print(f"   Audit Verify status: {resp.status_code}")
    assert resp.status_code == 200

if __name__ == "__main__":
    test_integration()
