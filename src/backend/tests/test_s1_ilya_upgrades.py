
import sys
import os
import json
from pathlib import Path
from dataclasses import asdict

# Add 'src' directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.relationship_engine.s1_neuro_symbolic import S1NeuroSymbolicEngine, ReasoningTrace

def test_ilya_upgrades():
    print("Initializing S1NeuroSymbolicEngine with upgrades...")
    engine = S1NeuroSymbolicEngine()
    
    # Test Case 1: Intermediate Halting (Value Function)
    print("\n--- Testing Intermediate Halting (Value Function) ---")
    # This scenario includes "Gambling" which should trigger a halt in our simulated reasoning steps
    # Or rather, we need to ensure the steering subsystem sees "Gambling" in the steps
    
    # Since we simulated the steps in s1_neuro_symbolic.py, let's look at them:
    # "Reviewing loan request for alignment with Green Energy Policy."
    # "Analyzing LTV ratio against Tier 1 and Tier 2 thresholds."
    # "Checking for any prohibited industry involvement (e.g. Gambling, etc.)."
    # "Synthesizing final recommendation..."
    
    # We will pass a query that triggers the system 2 loop
    scenario = "Requesting a loan for a Solar field next to a Casino (Gambling industry)."
    
    result = engine.process_query(scenario)
    
    print(f"Scenario: {scenario}")
    print(f"Halt Detected: {'Process halted' in result['analysis']}")
    
    # Verify Trace
    trace = result['trace']
    failed_steps = [t for t in trace if t['status'] == 'FAIL']
    
    if failed_steps:
        print(f"PASS: Value Function halted at step: {failed_steps[0]['thought']}")
        print(f"Feedback: {result['analysis']}")
    else:
        print("FAIL: Value Function failed to halt prohibited reasoning.")

    # Test Case 2: Continual Learning Log
    print("\n--- Testing Continual Learning Log ---")
    log_path = Path("data/training/continual_learning_stream.jsonl")
    if log_path.exists():
        with open(log_path, "r") as f:
            lines = f.readlines()
            if lines:
                last_log = json.loads(lines[-1])
                print(f"PASS: Log found with feedback: {last_log.get('feedback')}")
            else:
                print("FAIL: Log file is empty.")
    else:
        print("FAIL: Continual learning log file not found.")

if __name__ == "__main__":
    test_ilya_upgrades()
