import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import sys
import json
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).parent))

from relationship_engine.guardrails import FinancialGuardrails
from relationship_engine.adverse_action import AdverseActionReasoner
from relationship_engine.fairness_monitor import FairnessMonitor
from relationship_engine.context_assembler import ContextAssembler, execute_tool, Entitlement
from privacy_engine import PrivacyScorer
from policy_engine import PolicyEngine
from audit_vault import AuditVault
from cross_sell_engine import CrossSellOptimizer
from api_utils import APIResponse, APIError, ErrorCodes

app = FastAPI(
    title="PNC Strategic Foundry API",
    description="Backend API for Customer 360 and Relationship Intelligence",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Engines
assembler = ContextAssembler()
project_root = Path(__file__).parent.parent.parent
policy_engine = PolicyEngine(persist_dir=str(project_root / "data" / "policy_index"))
guardrails = FinancialGuardrails()
audit_vault = AuditVault(storage_path=str(project_root / "data" / "audit_log.jsonl"))
cross_sell_optimizer = CrossSellOptimizer(data_dir=str(project_root / "data" / "relationship_store" / "resolved"))
adverse_action_reasoner = AdverseActionReasoner()
fairness_monitor = FairnessMonitor()
privacy_scorer = PrivacyScorer(entities_path=project_root / "data" / "relationship_store" / "resolved" / "unified_entities.json")

@app.get("/")
async def root():
    return APIResponse.success(message="PNC Strategic Foundry API is operational")

@app.get("/api/v1/business/opportunities")
async def get_opportunities():
    """Retrieve strategic cross-sell opportunities from the entity graph."""
    try:
        opps = cross_sell_optimizer.analyze_opportunities()
        return APIResponse.success(opps)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/audit/logs")
async def get_audit_logs(limit: int = 20):
    """Retrieve recent immutable audit records."""
    try:
        records = audit_vault.get_records(limit=limit)
        return APIResponse.success(records)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/audit/verify")
async def verify_audit_chain():
    """Verify the cryptographic integrity of the entire audit vault."""
    try:
        result = audit_vault.verify_integrity()
        return APIResponse.success(result)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/identity/pending-reviews")
async def get_pending_reviews():
    """Retrieve identity matches that require human bank officer approval."""
    try:
        # Load match scores
        path = project_root / "data" / "relationship_store" / "resolved" / "match_scores.json"
        if not path.exists():
            return APIResponse.success([])
            
        with open(path, "r") as f:
            matches = json.load(f)
            
        # Filter for REVIEW_REQUIRED
        pending = [m for m in matches if m["merge_action"] == "REVIEW_REQUIRED"]
        return APIResponse.success(pending)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/policy/search")
async def search_policy(q: str = Query(..., min_length=2)):
    """Semantic (Keyword-boosted) search for relevant bank policies."""
    try:
        results = policy_engine.search(q)
        return APIResponse.success(results)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/compliance/adverse-action")
async def generate_adverse_action(name: str, revenue: float, income: float, debt: float, credit: int):
    """
    Reg B Compliance: Generate a formal Adverse Action notice based on deterministic math.
    """
    try:
        # 1. Run guardrails
        payload = {
            "annual_revenue": revenue,
            "net_income": income,
            "annual_debt_service": debt,
            "personal_credit_score": credit
        }
        g_result = guardrails.verify_sba_eligibility(payload)
        
        # 2. Generate notice
        notice = adverse_action_reasoner.generate_notice(name, g_result)
        return APIResponse.success(notice)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/compliance/privacy-risk")
async def get_privacy_risk(city: Optional[str] = None, zip: Optional[str] = None, type: str = "PERSON"):
    """
    GLBA Compliance: Calculate K-Anonymity privacy score for a set of attributes.
    """
    try:
        attrs = {"entity_type": type}
        if city: attrs["city"] = city
        if zip: attrs["zip5"] = zip
        
        k = privacy_scorer.calculate_anonymity_score(attrs)
        risk = privacy_scorer.get_risk_level(k)
        
        return APIResponse.success({
            "k_anonymity": k,
            "risk_level": risk,
            "attributes_checked": attrs
        })
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/customer/{name_or_id}")
async def get_customer(name_or_id: str, role: str = "ADMIN"):
    """Retrieve full Customer 360 view, filtered by role-based entitlements."""
    try:
        # Map simple role to entitlements
        ent_map = {
            "RETAIL": [Entitlement.RETAIL],
            "COMMERCIAL": [Entitlement.COMMERCIAL],
            "WEALTH": [Entitlement.WEALTH],
            "ADMIN": [Entitlement.ADMIN]
        }
        entitlements = ent_map.get(role.upper(), [Entitlement.ADMIN])
        
        data = assembler.get_customer_360(name_or_id, entitlements=entitlements)
        
        if not data:
            return APIResponse.error(f"Customer '{name_or_id}' not found", code=ErrorCodes.NOT_FOUND)
        
        # asdict if it's a dataclass, otherwise assume it's a dict or serializable
        if hasattr(data, "to_dict"):
            data = data.to_dict()
        elif hasattr(data, "__dict__"):
             from dataclasses import asdict, is_dataclass
             if is_dataclass(data):
                 data = asdict(data)

        return APIResponse.success(data)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/household/{name}")
async def get_household(name: str):
    """Retrieve aggregated household financial summary."""
    try:
        data = assembler.get_household_summary(name)
        if not data or not data.get("members"):
            return APIResponse.error(f"Household '{name}' not found or has no members", code=ErrorCodes.NOT_FOUND)
        
        return APIResponse.success(data)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/search")
async def search(q: str = Query(..., min_length=2)):
    """Search for entities (Person or Business) by name."""
    try:
        results = assembler.search_entities(q)
        return APIResponse.success(results)
    except Exception as e:
        return APIResponse.error(str(e))

@app.get("/api/v1/graph/data")
async def get_graph_data():
    """Retrieve the unified entity graph as nodes and edges for visualization."""
    try:
        # Load unified entities
        path = project_root / "data" / "relationship_store" / "resolved" / "unified_entities.json"
        with open(path, "r") as f:
            entities = json.load(f)
        
        # Load relationships
        rel_path = project_root / "data" / "relationship_store" / "resolved" / "relationships.json"
        with open(rel_path, "r") as f:
            relationships = json.load(f)

        nodes = []
        for e in entities:
            nodes.append({
                "id": e["unified_id"],
                "name": e["canonical_name"],
                "group": e["entity_type"],
                "val": 10 if e["entity_type"] == "BUSINESS" else 5
            })
        
        links = []
        for r in relationships:
            # Note: We need to map source_ids to unified_ids or just use names if unique
            # For this prototype, we'll try to find the unified_id by name
            links.append({
                "source": r["entity1_name"], # Simplified for demo
                "target": r["entity2_name"],
                "type": r["relationship_type"]
            })
            
        # Refine nodes to use names as IDs if links use names
        # In a real app, you'd use unified_ids everywhere
        demo_nodes = [{"id": n["name"], "group": n["group"]} for n in nodes]

        return APIResponse.success({"nodes": demo_nodes, "links": links})
    except Exception as e:
        return APIResponse.error(str(e))

@app.post("/api/v1/advisor/query")
async def advisor_query(payload: Dict[str, Any]):
    """
    Experimental: Process an advisor query through the reasoning pipeline.
    This simulates the S1 Reasoning flow and logs results to the Audit Vault.
    """
    query = payload.get("query")
    advisor_id = payload.get("advisor_id", "ANONYMOUS")
    model_mode = payload.get("model_mode", "cloud") # "cloud" (Teacher) or "local" (Student)
    
    if not query:
        return APIResponse.error("Query is required", code=ErrorCodes.INVALID_PARAMETER)
    
    try:
        from relationship_engine.s1_advisor_demo import S1ReasoningEngine
        engine = S1ReasoningEngine()
        # Pass the mode to the engine (requires update to S1ReasoningEngine.process_query signature too)
        # Note: We need to update S1ReasoningEngine wrapper to accept this kwarg.
        # For now, let's assume we update S1ReasoningEngine as well.
        result = engine.process_query(query, mode=model_mode)
        
        # Fair Lending Check: Scan for prohibited factors
        is_flagged, factors = fairness_monitor.scan_trace(result.get("response", ""))
        if is_flagged:
            result["fairness_warning"] = {
                "flagged": True,
                "prohibited_factors_found": factors,
                "action": "Response sanitized for fair lending compliance"
            }
            result["response"] = fairness_monitor.sanitize_trace(result["response"])

        # Log to Immutable Audit Vault
        audit_vault.log_event(
            advisor_id=advisor_id,
            query=query,
            reasoning_trace=result.get("reasoning_trace", []),
            response=result.get("response", ""),
            metadata={"source": "api_v1", "fairness_flagged": is_flagged}
        )
        
        return APIResponse.success(result)
    except ImportError:
        return APIResponse.error("Reasoning Engine not configured on this server")
    except Exception as e:
        return APIResponse.error(str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
