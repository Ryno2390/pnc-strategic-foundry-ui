
import sys
from unittest.mock import MagicMock

# MOCK google.generativeai BEFORE importing the module
mock_genai = MagicMock()
sys.modules["google.generativeai"] = mock_genai
sys.modules["google"] = MagicMock()

import unittest
from backend.relationship_engine.s1_neuro_symbolic import S1NeuroSymbolicEngine
from backend.relationship_engine.steering_subsystem import SteeringSubsystem

class TestSteeringLoop(unittest.TestCase):
    def setUp(self):
        # Mock the API key logic so it doesn't fail init
        self.engine = S1NeuroSymbolicEngine(api_key="TEST_KEY")
        
        # Mock the model
        self.engine.model = MagicMock()

    def test_steering_negative_feedback_loop(self):
        """
        Test that high LTV triggers the Steering Subsystem and forces re-reasoning.
        """
        # Scenario: High Risk LTV
        scenario = "Project 'RiskMax': 85% LTV requested for Solar Field."
        
        # 1. Mock Extraction (Checklist)
        # 2. Mock Initial Analysis -> "APPROVED" (This should trigger the Alarm)
        # 3. Mock Re-Analysis -> "DENIED" (After Feedback)
        
def side_effect(prompt):
            prompt_str = str(prompt)
            if "Extract the 'First Principles'" in prompt_str:
                return MagicMock(text="1. Check LTV limit.")
            elif "INTERNAL CHECKLIST" in prompt_str and "PREVIOUS ANALYSIS" not in prompt_str:
                # Initial Student Attempt (Naively Approves)
                return MagicMock(text="Analysis: Project looks good.\nDecision: APPROVED")
            elif "STEERING FEEDBACK (CRITICAL)" in prompt_str:
                # Student Correction after Pain Signal
                return MagicMock(text="Analysis: Re-evaluating. LTV 85% exceeds 80% limit.\nDecision: DENIED")
            else:
                return MagicMock(text="Unknown prompt")

        self.engine.model.generate_content.side_effect = side_effect
        
        # Run the loop
        result = self.engine._run_system_2_loop(scenario)
        
        # Verify Steering Trace exists
        self.assertIn("steering_trace", result)
        trace = result["steering_trace"]
        
        # Verify Feedback was generated
        print(f"\nSteering Trace: {trace}")
        
        has_negative_feedback = any("CRITICAL RISK" in t for t in trace)
        self.assertTrue(has_negative_feedback, "Should have detected Critical Risk")
        
        has_re_evaluation = any("Re-evaluating" in t for t in trace)
        self.assertTrue(has_re_evaluation, "Should have triggered re-evaluation")
        
        # Verify Final Response reflects the correction
        self.assertIn("Decision: DENIED", result["response"])

if __name__ == "__main__":
    unittest.main()
