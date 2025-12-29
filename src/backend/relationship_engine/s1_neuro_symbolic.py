"""
PNC Strategic Foundry - S1 Neuro-Symbolic Engine
================================================
Implements the "System 2" Reasoning Loop:
1. Retrieval: Fetch relevant policy + Golden Examples
2. Extraction: S1 (Teacher) extracts "First Principles" (Checklist)
3. Application: S1 (Student) applies Checklist to the scenario

This module integrates the "X-Scaling" insights into the Advisor pipeline.
"""

import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

# Add import
from backend.relationship_engine.flash_card_generator import FlashCardGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PNC.S1.NeuroSymbolic")

@dataclass
class ReasoningTrace:
    step: int
    thought: str
    checklist_item: Optional[str] = None
    status: Optional[str] = None # PASS / FAIL / WARN

class S1NeuroSymbolicEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("No GEMINI_API_KEY found. S1 Neuro-Symbolic will fail on generation.")
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Load local policies (simulated retrieval for now)
        self.policy_path = Path("data/policies/pnc_green_energy_transition_policy.md")
        self.examples_path = Path("src/backend/research/data/green_energy_examples.json")
        self.policy_text = self._load_file(self.policy_path)
        self.examples = json.loads(self._load_file(self.examples_path))

    def _load_file(self, path: Path) -> str:
        if path.exists():
            with open(path, "r") as f:
                return f.read()
        return ""

    def process_query(self, query: str, mode: str = "cloud") -> Dict[str, Any]:
        """
        Full System 2 Loop:
        1. Detect if this is a complex policy question.
        2. If so, extract checklist -> apply.
        3. Else, fallback to standard response (simulated).
        
        Args:
            query: The user's question.
            mode: "cloud" (Teacher/API) or "local" (Student/MLX).
        """
        logger.info(f"Processing query: {query} [Mode: {mode.upper()}]")
        
        # Heuristic: Is this a Green Energy policy question?
        if "solar" in query.lower() or "wind" in query.lower() or "battery" in query.lower() or "ltv" in query.lower():
            if mode == "local":
                return self._run_local_student(query)
            else:
                return self._run_system_2_loop(query)
        
        return {
            "response": "This query does not trigger the Neuro-Symbolic Policy Engine. Standard advisor flow would apply.",
            "mode": "System 1 (Standard)"
        }

    def _run_local_student(self, scenario: str) -> Dict[str, Any]:
        """
        Runs the 'Student' model (Local MLX) which has been distilled 
        to mimic the Teacher's reasoning.
        """
        try:
            from mlx_lm import load, generate
            
            # Path to the distilled adapter (check if it exists)
            adapter_path = "pnc_advisor_adapter"
            model_name = "Qwen/Qwen2.5-3B-Instruct"
            
            if os.path.exists(adapter_path):
                logger.info(f"Loading Local Student: {model_name} + {adapter_path}")
                model, tokenizer = load(model_name, adapter_path=adapter_path)
            else:
                logger.warning("Adapter not found. Loading Base Student Model (No Distillation).")
                model, tokenizer = load(model_name)
            
            # Construct Prompt (Student format)
            prompt = f"<|im_start|>system\nYou are the PNC Strategic Advisor. Analyze the loan request using the Green Energy Policy Checklist.<|im_end|>\n<|im_start|>user\n{scenario}<|im_end|>\n<|im_start|>assistant\n"
            
            response = generate(model, tokenizer, prompt=prompt, max_tokens=512, verbose=False)
            
            # Generate a generic card for the local student (distilled weights)
            card = FlashCardGenerator.generate_decision_card(
                "Local Student Analysis",
                "ANALYZED",
                {"Mode": "On-Device (MLX)", "Latency": "Low"},
                ["Reasoning generated locally", "Checklist implicit in weights"]
            )
            
            return {
                "mode": "System 2 (Local Student)",
                "checklist": "Implicit in Student Weights (Distilled)",
                "analysis": response,
                "response": response,
                "artifact": card
            }
            
        except ImportError:
            return {"error": "mlx_lm not installed. Cannot run local student."}
        except Exception as e:
            logger.error(f"Local Student Failed: {e}")
            return {"error": f"Local Student Error: {e}"}

    def _run_system_2_loop(self, scenario: str) -> Dict[str, Any]:
        if not self.model:
            return {"error": "Model not initialized (Missing API Key)"}

        # Step 1: Extract First Principles (The "Teacher" Step)
        # We cache this in production, but here we generate on fly or use cached.
        checklist = self._extract_checklist()
        
        # Step 2: Apply Logic (The "Student" Step)
        analysis = self._apply_checklist(checklist, scenario)
        
        # Step 3: Generate Flash Card Artifact
        # We parse the analysis to find the decision and key points
        decision = "FLAGGED" # Default/Safe
        if "APPROVED" in analysis.upper(): decision = "APPROVED"
        if "DENIED" in analysis.upper(): decision = "DENIED"
        
        # Extract a few bullets (heuristic: lines starting with * or -)
        bullets = [line.strip() for line in analysis.split('\\n') if line.strip().startswith(('*', '-'))][:3]
        if not bullets: bullets = ["Complex policy analysis required.", "See full text for details."]
        
        # Extract LTV if present
        ltv = "N/A"
        import re
        ltv_match = re.search(r"(\\d+%) LTV", scenario)
        if ltv_match: ltv = ltv_match.group(1)
        
        card = FlashCardGenerator.generate_decision_card(
            "Policy Analysis",
            decision,
            {"LTV Requested": ltv, "Policy Limit": "50% (Tier 2) / 80% (Tier 1)", "Review Type": "Neuro-Symbolic"},
            bullets
        )
        
        return {
            "mode": "System 2 (Neuro-Symbolic)",
            "checklist": checklist,
            "analysis": analysis,
            "response": analysis,  # For API compatibility
            "artifact": card
        }

    def _extract_checklist(self) -> str:
        """
        Asks the model to build a mental model (checklist) based on policy + examples.
        """
        prompt = f"""
        You are the Chief Credit Officer at PNC.
        
        POLICY TEXT:
        {self.policy_text}
        
        GOLDEN EXAMPLES (Precedent):
        {json.dumps(self.examples, indent=2)}
        
        TASK:
        Extract the 'First Principles' (The logic) and build a concise 'Underwriting Checklist' 
        for this specific policy. Output ONLY the numbered checklist.
        """
        
        # In a real app, check cache first
        response = self.model.generate_content(prompt)
        return response.text

    def _apply_checklist(self, checklist: str, scenario: str) -> str:
        """
        Forces the model to reason strictly against the extracted checklist.
        """
        prompt = f"""
        You are a PNC Strategic Advisor.
        
        INTERNAL CHECKLIST (The Law):
        {checklist}
        
        NEW LOAN REQUEST:
        {scenario}
        
        TASK:
        1. Analyze the request against each item in your checklist.
        2. Provide a final Decision: APPROVED, DENIED, or FLAGGED.
        3. Explain your reasoning for the final decision clearly.
        """
        
        response = self.model.generate_content(prompt)
        return response.text

if __name__ == "__main__":
    # Test Run
    engine = S1NeuroSymbolicEngine()
    test_case = "Project 'NeonFuture': 50MW Solar field. Sodium-Ion batteries. 12-year Amazon PPA. Requesting 75% LTV."
    result = engine.process_query(test_case)
    print(json.dumps(result, indent=2))
