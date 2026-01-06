
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.backend.relationship_engine.s1_neuro_symbolic import S1NeuroSymbolicEngine

def test_s1_v2_features():
    engine = S1NeuroSymbolicEngine()
    
    print("\n=== TEST 1: Standard Green Energy Request ===")
    scenario_1 = "Project 'Alpha': 10MW Solar field. Requesting 75% LTV. Strong cash flows."
    result_1 = engine.process_query(scenario_1)
    print(f"Mode: {result_1.get('mode')}")
    print(f"Liquid Dynamics Active: {{'volatility_index' in str(result_1.get('response'))}}")
    
    print("\n=== TEST 2: High Volatility Request (Liquid Dynamics Trigger) ===")
    scenario_2 = "Project 'Beta': 50MW Wind farm. Requesting 75% LTV. Note: Market volatility is extremely high due to a recent crash."
    result_2 = engine.process_query(scenario_2)
    print(f"Mode: {result_2.get('mode')}")
    # Should see Phase -1 in response
    if "Phase -1" in result_2.get('response', ''):
        print("SUCCESS: Liquid Dynamics Triggered.")
    else:
        print("FAILURE: Liquid Dynamics NOT Triggered.")

    print("\n=== TEST 3: Multi-Agent & Deliberation Check ===")
    # Check if we have multiple candidates in the log or trace
    response_text = result_2.get('response', '')
    if "Phase 2: Multi-Agent 'Red Teaming'" in response_text:
        print("SUCCESS: Multi-Agent Red Teaming executed.")
    if "Phase 3: Test-Time Compute" in response_text:
        print("SUCCESS: Test-Time Compute (Best-of-N) executed.")

if __name__ == "__main__":
    test_s1_v2_features()
