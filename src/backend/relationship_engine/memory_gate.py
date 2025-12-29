"""
PNC Strategic Foundry - Bayesian Memory Gate
============================================
Implements a "Surprise Filter" based on Information Gain (KL Divergence Proxy).

The Gate maintains a "User Belief State" (The Prior).
When new data arrives:
1.  It predicts the likelihood of the data given the Prior.
2.  It calculates a "Surprise Score" (0.0 - 1.0).
3.  If Score > Threshold: The data is committed to Long-Term Memory (The Foundry).
    Else: It is processed for the session but discarded from the permanent record.
"""

import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PNC.MemoryGate")

@dataclass
class MemoryDecision:
    input_text: str
    surprise_score: float
    decision: str  # COMMIT or DISCARD
    reasoning: str

class BayesianMemoryGate:
    def __init__(self, api_key: str = None, surprise_threshold: float = 0.7):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            logger.warning("No API Key. Memory Gate will default to PASS_THROUGH.")
            self.model = None
            
        self.surprise_threshold = surprise_threshold
        
        # In a real system, this would be loaded from a Vector DB
        self.user_belief_state = "Client is a conservative manufacturing firm in the Midwest. CEO focuses on steady cash flow and low debt. No M&A activity in past 5 years."

    def process_interaction(self, user_input: str) -> MemoryDecision:
        """
        Calculates the Information Gain of the new input against the Belief State.
        """
        if not self.model:
            return MemoryDecision(user_input, 0.0, "DISCARD", "No Model")

        surprise, reasoning = self._calculate_information_gain(user_input)
        
        decision = "COMMIT" if surprise >= self.surprise_threshold else "DISCARD"
        
        # If committed, we ideally update the belief state (simulated here)
        if decision == "COMMIT":
            self.user_belief_state += f" [UPDATE: {user_input}]"
            
        return MemoryDecision(
            input_text=user_input,
            surprise_score=surprise,
            decision=decision,
            reasoning=reasoning
        )

    def _calculate_information_gain(self, observation: str) -> Tuple[float, str]:
        """
        Uses the LLM to estimate the 'Surprise' (KL Divergence proxy).
        """
        prompt = f"""
        You are a Bayesian Surprise Filter for a Bank CEO's memory.
        
        CURRENT BELIEF STATE (The Prior):
        "{self.user_belief_state}"
        
        NEW OBSERVATION (The Data):
        "{observation}"
        
        TASK:
        Rate the "Information Gain" (Surprise) of this new observation.
        - 0.0: Completely expected, redundant, or noise (e.g., "Hi", "Thanks", "Checking balance").
        - 0.5: Minor update or clarification.
        - 1.0: Paradigm shift, contradiction, or major strategic pivot (e.g., "Selling the company").
        
        OUTPUT JSON ONLY:
        {{
            "score": 0.X,
            "reasoning": "Why this is low/high surprise."
        }}
        """
        
        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            return float(data.get("score", 0.0)), data.get("reasoning", "")
        except Exception as e:
            logger.error(f"Error calculating surprise: {e}")
            return 0.0, "Error"

if __name__ == "__main__":
    # Quick Test
    gate = BayesianMemoryGate()
    
    inputs = [
        "Hi, how are you today?",
        "I need to check the balance on my operating account.",
        "We are thinking of acquiring our largest competitor in Mexico."
    ]
    
    print(f"INITIAL BELIEF: {gate.user_belief_state}\n")
    
    for i in inputs:
        result = gate.process_interaction(i)
        print(f"INPUT: '{i}'")
        print(f"  Surprise: {result.surprise_score}")
        print(f"  Decision: {result.decision}")
        print(f"  Reason:   {result.reasoning}\n")
