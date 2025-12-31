
import sys
import os
import json
from pathlib import Path

# Add 'src' directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.relationship_engine.steering_subsystem import SteeringSubsystem

def test_taste_logic():
    print("Initializing SteeringSubsystem for Taste verification...")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY required for this test.")
        return

    steering = SteeringSubsystem(api_key=api_key)
    
    # Scenario: Jagged/Repetitive reasoning (Violates 'Precision' principle)
    jagged_reasoning = "The loan is good because it is a loan and loans are good for the bank because the bank likes loans that are good. We should approve the loan because loans are good."
    context = "Small business loan for a bakery."
    
    print(f"\n--- Testing Jagged Reasoning (Taste Check) ---")
    print(f"Reasoning: {jagged_reasoning}")
    signal = steering.evaluate_intermediate_step(jagged_reasoning, context)
    
    print(f"Is Safe: {signal.is_safe}")
    print(f"Score: {signal.reward_score}")
    print(f"Feedback: {signal.feedback}")
    print(f"Source: {signal.source}")

    # Scenario: Principle Alignment (Favors bank stability)
    principled_reasoning = "While the client's growth is impressive, the 95% LTV on this specialized equipment poses a significant risk to the bank's stability in a downturn. I recommend capping the LTV at 75%."
    print(f"\n--- Testing Principled Reasoning (Taste Check) ---")
    print(f"Reasoning: {principled_reasoning}")
    signal_2 = steering.evaluate_intermediate_step(principled_reasoning, context)
    
    print(f"Is Safe: {signal_2.is_safe}")
    print(f"Score: {signal_2.reward_score}")
    print(f"Feedback: {signal_2.feedback}")
    print(f"Source: {signal_2.source}")

if __name__ == "__main__":
    test_taste_logic()
