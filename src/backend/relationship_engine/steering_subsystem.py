"""
PNC Strategic Foundry - Steering Subsystem
==========================================
Implements the "Steering vs. Learning" architecture inspired by Adam Marblestone.

The Steering Subsystem represents the "innate" values of the organism (PNC),
encoded as hard, fast, and biologically/institutionally "expensive" to violate.

It provides a "Reward Signal" or "Loss Function" to the S1 Learning System.
"""

import logging
import os
import json
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import re
import google.generativeai as genai

# Configure logging
logger = logging.getLogger("PNC.SteeringSubsystem")

@dataclass
class RewardSignal:
    is_safe: bool
    reward_score: float  # -1.0 to 1.0
    feedback: str
    source: str # "Risk_Appetite", "Ethics", "Compliance"
    is_terminal: bool = False # Whether this signal should halt the reasoning immediately

class SteeringSubsystem:
    """
    The Steering Subsystem represents the 'innate' values of PNC.
    It has been enhanced with 'Principle-based' evaluation (Taste) to solve model jaggedness.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.risk_thresholds = {
            "LTV_MAX": 80.0, # Loan-to-Value
            "DSCR_MIN": 1.15, # Debt Service Coverage Ratio
        }
        self.prohibited_industries = ["Gambling", "Adult Entertainment", "Predatory Lending"]
        
        # Principles for "Taste"
        self.guiding_principles = [
            "Precision: Avoid repetitive or 'jagged' reasoning.",
            "Conservatism: When in doubt, favor the bank's long-term stability.",
            "Client-Centricity: Solutions must benefit both PNC and the client.",
            "Regulatory Spirit: Follow the intent of the law, not just the letter."
        ]
        
        # Initialize Gemini for 'Taste' evaluation (Principle-based Steering)
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.eval_model = genai.GenerativeModel('gemini-2.0-flash') # Using flash for efficiency
        else:
            self.eval_model = None

    def evaluate_intermediate_step(self, step_thought: str, context: str) -> RewardSignal:
        """
        The 'Value Function' - evaluates intermediate reasoning steps to catch errors early.
        """
        # Fast Symbolic Checks
        for industry in self.prohibited_industries:
            if industry.lower() in step_thought.lower():
                return RewardSignal(
                    is_safe=False,
                    reward_score=-1.0,
                    feedback=f"Intermediate step touched on prohibited industry: {industry}",
                    source="Brainstem_ValueFunction",
                    is_terminal=True
                )
        
        # Semantic 'Taste' Check (only if API key available)
        if self.eval_model:
            return self._evaluate_taste(step_thought, context)

        return RewardSignal(True, 0.1, "Step seems reasonable.", "ValueFunction_Heuristic")

    def _evaluate_taste(self, reasoning: str, context: str) -> RewardSignal:
        """
        Uses an LLM to judge if the reasoning exhibits 'Model Jaggedness' or lack of 'Taste'.
        """
        prompt = f"""
        You are the 'Taste' module for a banking AI. 
        Evaluate the following reasoning step for 'jaggedness' (repetitive, nonsensical, or unprincipled logic).
        
        GUIDING PRINCIPLES:
        {json.dumps(self.guiding_principles, indent=2)}
        
        CONTEXT:
        {context}
        
        REASONING STEP:
        {reasoning}
        
        Does this step align with our guiding principles? 
        Respond in JSON format: {{"is_safe": bool, "score": float (-1 to 1), "feedback": "string"}}
        """
        try:
            response = self.eval_model.generate_content(prompt)
            # Basic parsing of JSON from response
            res_text = response.text.strip()
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            
            data = json.loads(res_text)
            return RewardSignal(
                is_safe=data.get("is_safe", True),
                reward_score=data.get("score", 0.0),
                feedback=data.get("feedback", "No specific feedback."),
                source="Taste_Evaluator"
            )
        except Exception as e:
            logger.warning(f"Taste evaluation failed: {e}")
            return RewardSignal(True, 0.0, "Taste evaluation bypassed.", "Taste_Evaluator_Fallback")

    def evaluate_recommendation(self, scenario: str, analysis: str, domain: str = "commercial_lending") -> RewardSignal:
        # 1. Parse Intent (Simple Heuristic for Demo)
        decision = "NEUTRAL"
        if "APPROVED" in analysis.upper(): decision = "APPROVED"
        if "DENIED" in analysis.upper(): decision = "DENIED"
        
        # 2. Universal Ethical/Regulatory Checks (The "Brainstem")
        for industry in self.prohibited_industries:
            if industry.lower() in scenario.lower() and decision == "APPROVED":
                return RewardSignal(
                    is_safe=False,
                    reward_score=-1.0,
                    feedback=f"ETHICAL VIOLATION: Transaction involves prohibited industry '{industry}'. Immediate blocking signal.",
                    source="Ethics_Brainstem",
                    is_terminal=True
                )

        # 3. Domain-Specific Reward Functions
        if domain == "commercial_lending":
            return self._evaluate_commercial_lending(scenario, analysis, decision)
        
        return RewardSignal(True, 0.0, "Neutral: No domain specific rules triggered.", "Homeostasis")

    def _evaluate_commercial_lending(self, scenario: str, analysis: str, decision: str) -> RewardSignal:
        ltv = self._extract_ltv(scenario)
        is_green = "solar" in scenario.lower() or "wind" in scenario.lower()
        
        if ltv and ltv > self.risk_thresholds["LTV_MAX"]:
            if decision == "APPROVED":
                return RewardSignal(
                    is_safe=False,
                    reward_score=-1.0,
                    feedback=f"CRITICAL RISK: Proposed LTV {ltv}% exceeds hard cap of {self.risk_thresholds['LTV_MAX']}%.",
                    source="Risk_Appetite_Amygdala",
                    is_terminal=True
                )
        
        if is_green and decision == "APPROVED":
             return RewardSignal(
                is_safe=True,
                reward_score=0.8,
                feedback="Positive Reinforcement: Aligns with Strategic Goal 'Green Transition'.",
                source="Strategic_Nucleus_Accumbens"
            )

        return RewardSignal(True, 0.1, "Safe commercial lending decision.", "Commercial_Cortex")

    def _extract_ltv(self, text: str) -> Optional[float]:
        match = re.search(r"(\d+(\.\d+)?)%\s*LTV", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

