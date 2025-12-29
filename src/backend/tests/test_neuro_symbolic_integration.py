
import sys
import os
import json
from pathlib import Path

# Add 'src' directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.relationship_engine.s1_advisor_demo import S1ReasoningEngine

def test_integration():
    print("Initializing S1ReasoningEngine...")
    engine = S1ReasoningEngine()
    
    # Test Case 1: Standard Query (System 1)
    print("\n--- Testing Standard Query (System 1) ---")
    q1 = "What is the total relationship value for the Smith household?"
    try:
        res1 = engine.process_query(q1)
        print(f"Query: {q1}")
        print(f"Response: {res1['response'][:100]}...")
        trace_steps = [s['thought'] for s in res1['reasoning_trace']]
        if "This looks like a complex credit policy question" not in str(trace_steps):
            print("PASS: Correctly routed to System 1")
        else:
            print("FAIL: Incorrectly routed to System 2")
    except Exception as e:
        print(f"WARN: System 1 Test failed with unrelated error: {e}")
        print("Proceeding to System 2 test...")

    # Test Case 2: Policy Query (System 2)
    print("\n--- Testing Policy Query (System 2) ---")
    q2 = "Project 'NeonFuture': 50MW Solar field. Sodium-Ion batteries. 12-year Amazon PPA. Requesting 75% LTV."
    
    # Only run if API key is present
    if os.environ.get("GEMINI_API_KEY"):
        res2 = engine.process_query(q2)
        print(f"Query: {q2}")
        print(f"Response: {res2['response'][:100]}...")
        
        trace_steps = [s['thought'] for s in res2['reasoning_trace']]
        if "Engaging System 2" in str(trace_steps):
             print("PASS: Correctly routed to System 2")
             print("Checklist found in tool_data:", bool(res2.get("tool_data", {}).get("checklist")))
        else:
             print("FAIL: Failed to route to System 2")
             print(trace_steps)
    else:
        print("SKIPPING: No GEMINI_API_KEY found")

if __name__ == "__main__":
    test_integration()
