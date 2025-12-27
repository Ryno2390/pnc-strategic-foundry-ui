import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).parent))

from relationship_engine.context_assembler import ContextAssembler, execute_tool
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

# Initialize the Context Assembler
assembler = ContextAssembler()

@app.get("/")
async def root():
    return APIResponse.success(message="PNC Strategic Foundry API is operational")

@app.get("/api/v1/customer/{name_or_id}")
async def get_customer(name_or_id: str):
    """Retrieve full Customer 360 view for a person."""
    try:
        # The assembler expects entity_id_or_name
        data = assembler.get_customer_360(name_or_id)
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

@app.post("/api/v1/advisor/query")
async def advisor_query(payload: Dict[str, str]):
    """
    Experimental: Process an advisor query through the reasoning pipeline.
    This simulates the S1 Reasoning flow.
    """
    query = payload.get("query")
    if not query:
        return APIResponse.error("Query is required", code=ErrorCodes.INVALID_PARAMETER)
    
    try:
        # We can use the logic from s1_advisor_demo.py
        # For now, we'll import and use S1ReasoningEngine if available
        # or simulate a simplified version.
        from relationship_engine.s1_advisor_demo import S1ReasoningEngine
        engine = S1ReasoningEngine()
        result = engine.process_query(query)
        return APIResponse.success(result)
    except ImportError:
        return APIResponse.error("Reasoning Engine not configured on this server")
    except Exception as e:
        return APIResponse.error(str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
