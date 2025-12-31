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
from dataclasses import dataclass, asdict
from pathlib import Path

# Add import
from backend.relationship_engine.flash_card_generator import FlashCardGenerator
from backend.relationship_engine.steering_subsystem import SteeringSubsystem, RewardSignal

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
        self.model = None
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
        
        # Initialize Steering Subsystem (Innate Values)
        self.steering_subsystem = SteeringSubsystem()

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
        full_reasoning_log = []
        reasoning_trace: List[ReasoningTrace] = []

        # Step 1: Extract First Principles
        checklist = "[SIMULATED CHECKLIST] Policy alignment required."
        if self.model:
            checklist = self._extract_checklist()
        full_reasoning_log.append(f"### Phase 1: Policy Checklist Extracted\n{checklist}")

        # Step 2: Incremental Reasoning with Value Function (Intermediate Signals)
        # We simulate the incremental steps for this implementation
        steps = [
            "Reviewing loan request for alignment with Green Energy Policy.",
            "Analyzing LTV ratio against Tier 1 and Tier 2 thresholds.",
            "Checking for any prohibited industry involvement (e.g. Gambling, etc.).",
            "Synthesizing final recommendation based on credit risk and strategic alignment."
        ]

        final_analysis = ""
        interrupted = False

        for i, step_desc in enumerate(steps):
            # Evaluate intermediate step with Steering Subsystem (Value Function)
            signal = self.steering_subsystem.evaluate_intermediate_step(step_desc, scenario)
            
            trace_step = ReasoningTrace(
                step=i+1,
                thought=step_desc,
                status="PASS" if signal.is_safe else "FAIL"
            )
            reasoning_trace.append(trace_step)

            if not signal.is_safe:
                full_reasoning_log.append(f"\n[VALUE FUNCTION HALT] Step {i+1}: {signal.feedback}")
                final_analysis = f"Process halted due to safety violation: {signal.feedback}"
                interrupted = True
                # Log the halt for learning
                self._log_for_learning(scenario, final_analysis, signal)
                break

        if not interrupted:
            # Step 3: Final Application (The "Student" Step)
            if self.model:
                final_analysis = self._apply_checklist(checklist, scenario)
            else:
                final_analysis = "[SIMULATED] Loan application reviewed. Decision: APPROVED (Based on principles)."
            
            full_reasoning_log.append(f"\n### Phase 2: Final Cortex Analysis\n{final_analysis}")
            
            # Final Steering Check
            steering_signal = self.steering_subsystem.evaluate_recommendation(scenario, final_analysis)
            full_reasoning_log.append(f"\n### Phase 3: Steering Evaluation\n{steering_signal.feedback}")

            if not steering_signal.is_safe:
                if self.model:
                    final_analysis = self._re_reason_with_feedback(checklist, scenario, final_analysis, steering_signal.feedback)
                else:
                    final_analysis = f"[SIMULATED RE-REASON] Process adjusted based on feedback: {steering_signal.feedback}. Final Decision: DENIED."
                
                full_reasoning_log.append(f"\n### Phase 4: Revised Analysis\n{final_analysis}")
            
            # Log for Continual Learning
            self._log_for_learning(scenario, final_analysis, steering_signal)

        # Artifact Generation
        decision = "FLAGGED"
        if "APPROVED" in final_analysis.upper(): decision = "APPROVED"
        if "DENIED" in final_analysis.upper(): decision = "DENIED"
        
        bullets = [line.strip() for line in final_analysis.split('\n') if line.strip().startswith(('*', '-'))][:3]
        
        card = FlashCardGenerator.generate_decision_card(
            "Neuro-Symbolic Analysis",
            decision,
            {"Mode": "S1-Steered", "Safety": "Active"},
            bullets or ["Principles-based analysis complete."]
        )
        
        return {
            "mode": "System 2 (Neuro-Symbolic v2)",
            "trace": [asdict(t) for t in reasoning_trace],
            "analysis": final_analysis,
            "response": "\n".join(full_reasoning_log),
            "artifact": card
        }

    def _log_for_learning(self, scenario: str, result: str, signal: RewardSignal):
        """
        Saves the interaction and reward signal for future fine-tuning (Continual Learning).
        """
        log_entry = {
            "scenario": scenario,
            "result": result,
            "reward_score": signal.reward_score,
            "feedback": signal.feedback,
            "source": signal.source
        }
        log_path = Path("data/training/continual_learning_stream.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.info("Interaction logged for Continual Learning.")

    def _re_reason_with_feedback(self, checklist: str, scenario: str, previous_analysis: str, feedback: str) -> str:
        """
        Re-evaluates the scenario given strong negative feedback from the Steering Subsystem.
        """
        prompt = f"""
        You are a PNC Strategic Advisor.
        
        INTERNAL CHECKLIST (The Law):
        {checklist}
        
        NEW LOAN REQUEST:
        {scenario}
        
        PREVIOUS ANALYSIS (REJECTED):
        {previous_analysis}
        
        STEERING FEEDBACK (CRITICAL):
        {feedback}
        
        TASK:
        1. Acknowledge the feedback.
        2. Re-analyze the request strictly adhering to the feedback.
        3. Provide a revised Decision and Reasoning.
        """
        
        response = self.model.generate_content(prompt)
        return response.text

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