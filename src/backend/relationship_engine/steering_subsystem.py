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
import re
import torch
import torch.nn as nn
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
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

class RewardScorer(nn.Module):
    """
    A simple neural network to refine the reward score based on internal policy weights.
    In production, this would be a trained Process Reward Model (PRM).
    """
    def __init__(self):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(3, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
            nn.Tanh() # Output between -1 and 1
        )
    
    def forward(self, x):
        return self.fc(x)

class SteeringSubsystem:
    """
    The Steering Subsystem represents the 'innate' values of PNC.
    It has been enhanced with 'Liquid' dynamics, 'Taste' evaluation, and 'Torch-PRM' scoring.
    """
    def __init__(self, api_key: Optional[str] = None):
        # Base thresholds
        self.base_risk_thresholds = {
            "LTV_MAX": 80.0, 
            "DSCR_MIN": 1.15,
        }
        self.risk_thresholds = self.base_risk_thresholds.copy()
        
        # Volatility state (The 'Liquid' component)
        self.volatility_index = 0.0 # 0.0 (Calm) to 1.0 (Flash Crash)
        
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
            self.eval_model = genai.GenerativeModel('gemini-2.0-flash') 
        else:
            self.eval_model = None
            
        # Torch-based Process Reward Model (PRM)
        self.prm_model = RewardScorer()

    def liquify(self, stress_level: float):
        """
        Dynamically adjusts the 'physics' of the steering engine.
        As stress_level increases, the system becomes more conservative (Liquid Neural Network simulation).
        """
        self.volatility_index = max(0.0, min(1.0, stress_level))
        
        # Adjust LTV: In high stress, we want lower LTV (e.g., 80% -> 60%)
        ltv_reduction = self.volatility_index * 20.0
        self.risk_thresholds["LTV_MAX"] = self.base_risk_thresholds["LTV_MAX"] - ltv_reduction
        
        # Adjust DSCR: In high stress, we want higher DSCR (e.g., 1.15 -> 1.45)
        dscr_increase = self.volatility_index * 0.3
        self.risk_thresholds["DSCR_MIN"] = self.base_risk_thresholds["DSCR_MIN"] + dscr_increase
        
        logger.info(f"Steering Liquified: Stress={self.volatility_index:.2f}, LTV_MAX={self.risk_thresholds['LTV_MAX']:.1f}%")

    def _refine_with_torch(self, score: float, is_safe: bool, volatility: float) -> float:
        """
        Uses a Torch model to refine the final reward score based on multiple inputs.
        """
        try:
            input_tensor = torch.tensor([[score, 1.0 if is_safe else 0.0, volatility]], dtype=torch.float32)
            with torch.no_grad():
                refined_score = self.prm_model(input_tensor).item()
            return refined_score
        except Exception as e:
            logger.warning(f"Torch refinement failed: {e}")
            return score

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
        prompt = f"Judge this reasoning for 'taste' and 'jaggedness': {reasoning} Context: {context}"
        try:
            # Simplified for prototype, in reality use structured output
            response = self.eval_model.generate_content(prompt)
            return RewardSignal(True, 0.5, "Taste check passed (simulated).", "Taste_Evaluator")
        except Exception as e:
            return RewardSignal(True, 0.0, "Taste evaluation bypassed.", "Taste_Evaluator_Fallback")

    def evaluate_recommendation(self, scenario: str, analysis: str, domain: str = "commercial_lending") -> RewardSignal:
        # 1. Parse Intent
        decision = "NEUTRAL"
        if "APPROVED" in analysis.upper(): decision = "APPROVED"
        if "DENIED" in analysis.upper(): decision = "DENIED"
        
        # 2. Universal Ethical/Regulatory Checks
        for industry in self.prohibited_industries:
            if industry.lower() in scenario.lower() and decision == "APPROVED":
                return RewardSignal(False, -1.0, f"Prohibited industry: {industry}", "Ethics", True)

        # 3. Domain-Specific Reward Functions
        signal = RewardSignal(True, 0.1, "Safe decision.", "Homeostasis")
        if domain == "commercial_lending":
            signal = self._evaluate_commercial_lending(scenario, analysis, decision)
        
        # 4. Neural Refinement (Torch PRM)
        signal.reward_score = self._refine_with_torch(signal.reward_score, signal.is_safe, self.volatility_index)
        
        return signal

    def _evaluate_commercial_lending(self, scenario: str, analysis: str, decision: str) -> RewardSignal:
        ltv = self._extract_ltv(scenario)
        is_green = "solar" in scenario.lower() or "wind" in scenario.lower()
        
        if ltv and ltv > self.risk_thresholds["LTV_MAX"]:
            if decision == "APPROVED":
                return RewardSignal(False, -1.0, f"LTV {ltv}% exceeds cap {self.risk_thresholds['LTV_MAX']}%", "Risk", True)
        
        if is_green and decision == "APPROVED":
             return RewardSignal(True, 0.8, "Aligns with Green Transition.", "Strategic")

        return RewardSignal(True, 0.1, "Safe commercial lending.", "Commercial")

    def _extract_ltv(self, text: str) -> Optional[float]:
        match = re.search(r"(\d+(\.\d+)?)%\s*LTV", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None