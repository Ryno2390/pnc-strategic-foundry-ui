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
from backend.policy_graph_engine import PolicyGraphEngine
from backend.risk_graph import RiskGraph

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PNC.S1.NeuroSymbolic")

@dataclass
class ReasoningTrace:
    step: int
    thought: str
    checklist_item: Optional[str] = None
    status: Optional[str] = None # PASS / FAIL / WARN
    graph_path: Optional[List[str]] = None # New: Audit-Ready Graph Trace

class S1NeuroSymbolicEngine:
    # --- RED TEAM PROMPTS (Idea #2: Multi-Agent Systems) ---
    CHALLENGER_PROMPT = """
    You are the 'Red Team' Risk Analyst at PNC. 
    Your goal is to find every possible reason why this proposal should be REJECTED or FLAGGED.
    Analyze the scenario strictly against the checklist, but focus on:
    - Hidden risks and contagion.
    - Policy loopholes.
    - Potential 'jaggedness' or inconsistencies in the client's data.
    - Worst-case scenarios.

    CHECKLIST:
    {checklist}

    SCENARIO:
    {scenario}

    Provide a critical 'Risk Challenge' report.
    """

    DEFENDER_PROMPT = """
    You are the 'Blue Team' Relationship Manager at PNC.
    Your goal is to find every possible reason why this proposal should be APPROVED.
    Analyze the scenario strictly against the checklist, but focus on:
    - Strategic alignment with PNC's long-term goals (e.g., Green Energy Transition).
    - Mitigation factors already in place.
    - Relationship value and future growth.
    - How this proposal fulfills the 'spirit' of the policy.

    CHECKLIST:
    {checklist}

    SCENARIO:
    {scenario}

    Provide a 'Strategic Alignment' report.
    """

    AUDITOR_PROMPT = """
    You are the 'S1 Auditor'. You are the final decision-maker.
    You have received two conflicting reports:
    1. RED TEAM (Risk Challenge)
    2. BLUE TEAM (Strategic Alignment)

    Your task is to reconcile these views and produce a final 'Audit-Ready' Risk Reconciliation.
    You must:
    - Weigh the risks vs. rewards.
    - Ensure all checklist items are addressed.
    - Make a final Decision: APPROVED, DENIED, or FLAGGED.

    RED TEAM REPORT:
    {red_report}

    BLUE TEAM REPORT:
    {blue_report}

    FINAL RECONCILIATION:
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = None
        if not self.api_key:
            logger.warning("No GEMINI_API_KEY found. S1 Neuro-Symbolic will fail on generation.")
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Load local policies (simulated retrieval for now)
        project_root = Path(__file__).parent.parent.parent.parent
        self.policy_engine = PolicyGraphEngine(
            persist_dir=str(project_root / "data" / "policy_index"),
            graph_path=str(project_root / "data" / "risk_graph.json")
        )
        
        self.policy_path = Path("data/policies/pnc_green_energy_transition_policy.md")
        self.examples_path = Path("src/backend/research/data/green_energy_examples.json")
        self.policy_text = self._load_file(self.policy_path)
        if self.examples_path.exists():
            self.examples = json.loads(self._load_file(self.examples_path))
        else:
            self.examples = []
        
        # Initialize Steering Subsystem (Innate Values)
        self.steering_subsystem = SteeringSubsystem()

    def deliberate(self, scenario: str, checklist: str, n: int = 3) -> Dict[str, Any]:
        """
        Implements Test-Time Compute (Reasoning Scaling).
        Generates N candidate reasoning paths with varying temperature and picks the winner.
        """
        logger.info(f"Starting Deliberation (Test-Time Compute) with N={n}...")
        candidates = []

        for i in range(n):
            # Vary temperature for diversity (0.2, 0.7, 1.0)
            temp = 0.2 + (i * 0.4)
            
            if self.model:
                prompt = f"CHECKLIST:\n{checklist}\n\nSCENARIO:\n{scenario}\n\nTASK: Analyze strictly against checklist. Be thorough and logical."
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(temperature=temp)
                )
                candidate_text = response.text
                # Evaluate with Steering Subsystem (The Process Reward Model)
                signal = self.steering_subsystem.evaluate_recommendation(scenario, candidate_text)
            else:
                candidate_text = f"[SIMULATED CANDIDATE {i}] Analysis at temp {temp:.1f}."
                score = 0.7 + (i * 0.1) 
                signal = RewardSignal(is_safe=True, reward_score=score, feedback="Simulation pass", source="System")
            
            candidates.append({
                "id": i,
                "text": candidate_text,
                "reward_score": signal.reward_score,
                "temp": temp,
                "is_safe": signal.is_safe
            })
            logger.info(f"Candidate {i} (temp={temp:.1f}) scored: {signal.reward_score}")

        # Sort by reward score descending
        candidates.sort(key=lambda x: x["reward_score"], reverse=True)
        winner = candidates[0]
        
        logger.info(f"Deliberation complete. Winner: Candidate {winner['id']} (Score: {winner['reward_score']})")
        return {
            "winner": winner,
            "all_candidates": candidates
        }

    def multi_agent_red_team(self, scenario: str, checklist: str) -> Dict[str, Any]:
        """
        Implements Idea #2: Multi-Agent "Red Teaming" Systems.
        Deploys Challenger, Defender, and Auditor agents.
        The Challenger is augmented with RiskGraph contagion traces.
        """
        logger.info("Starting Multi-Agent Red Teaming debate...")
        
        # 0. Context Gathering (Graph-Augmented Risk)
        graph_risks = []
        if "sba" in scenario.lower():
            graph_risks = self.policy_engine.query_graph("SBA_7A_LOAN_POLICY")
        elif "green" in scenario.lower() or "solar" in scenario.lower():
            graph_risks = self.policy_engine.query_graph("PNC_GREEN_ENERGY_TRANSITION_POLICY")
        
        risk_context = ""
        if graph_risks:
            risk_context = "\nKNOWLEDGE GRAPH RISKS:\n" + "\n".join([f"- {r['node_id']}: {r['path'][-1]}" for r in graph_risks if r['type'] == 'Risk'][:5])

        if not self.model:
            return {
                "final_analysis": "[SIMULATED RED TEAM] Reconciliation complete. Decision: APPROVED.",
                "red_report": "Risk looks acceptable. " + risk_context,
                "blue_report": "Strategic alignment is strong."
            }

        # 1. Challenger (Red Team) - Augmented with Graph context
        red_response = self.model.generate_content(
            self.CHALLENGER_PROMPT.format(checklist=checklist, scenario=scenario + risk_context)
        )
        red_report = red_response.text

        # 2. Defender (Blue Team)
        blue_response = self.model.generate_content(
            self.DEFENDER_PROMPT.format(checklist=checklist, scenario=scenario)
        )
        blue_report = blue_response.text

        # 3. Auditor (Reconciliation)
        auditor_response = self.model.generate_content(
            self.AUDITOR_PROMPT.format(red_report=red_report, blue_report=blue_report)
        )
        final_analysis = auditor_response.text

        return {
            "final_analysis": final_analysis,
            "red_report": red_report,
            "blue_report": blue_report
        }

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

    def _liquify_if_needed(self, scenario: str):
        """
        Trigger the Liquid Neural Network simulation if high stress is detected.
        """
        stress_keywords = ["volatility", "crash", "recession", "high risk", "unstable", "contagion"]
        stress_level = 0.0
        
        for word in stress_keywords:
            if word in scenario.lower():
                stress_level += 0.3
        
        if stress_level > 0:
            logger.info(f"Liquid Dynamics Triggered: Stress Level {stress_level}")
            self.steering_subsystem.liquify(stress_level)

    def _run_system_2_loop(self, scenario: str) -> Dict[str, Any]:
        full_reasoning_log = []
        reasoning_trace: List[ReasoningTrace] = []

        # New: Phase -1 - Dynamic Context Gate (Liquidity)
        self._liquify_if_needed(scenario)
        if self.steering_subsystem.volatility_index > 0:
            full_reasoning_log.append(f"### Phase -1: Liquid Dynamics Active\n- Market Stress Index: {self.steering_subsystem.volatility_index:.2f}\n- Risk Thresholds tightened (LTV Max: {self.steering_subsystem.risk_thresholds['LTV_MAX']:.1f}%)")

        # New: Phase 0 - Graph-Based Risk Identification (Context Graph)
        graph_impact = []
        # Identify core policy node from query (heuristic for demo)
        if "sba" in scenario.lower():
            graph_impact = self.policy_engine.query_graph("SBA_7A_LOAN_POLICY")
        elif "green" in scenario.lower() or "solar" in scenario.lower():
            graph_impact = self.policy_engine.query_graph("PNC_GREEN_ENERGY_TRANSITION_POLICY")

        if graph_impact:
            graph_paths = [ " -> ".join(p['path']) for p in graph_impact[:3]] # Take top 3 paths
            full_reasoning_log.append(f"### Phase 0: Context Graph Traversal (Audit Trace)\n" + "\n".join([f"- {path}" for path in graph_paths]))
        
        # Step 1: Extract First Principles
        checklist = "[SIMULATED CHECKLIST] Policy alignment required."
        if self.model:
            checklist = self._extract_checklist()
        full_reasoning_log.append(f"### Phase 1: Policy Checklist Extracted\n{checklist}")

        # Step 2: Incremental Reasoning with Value Function (Intermediate Signals)
        steps = [
            "Reviewing loan request for alignment with Policy.",
            "Analyzing specific requirements identified in the Context Graph.",
            "Checking for any prohibited industry involvement or risk contagion.",
            "Synthesizing final recommendation based on credit risk and strategic alignment."
        ]

        final_analysis = ""
        interrupted = False

        for i, step_desc in enumerate(steps):
            # Evaluate intermediate step with Steering Subsystem (Value Function)
            signal = self.steering_subsystem.evaluate_intermediate_step(step_desc, scenario)
            
            relevant_graph_path = None
            if i == 1 and graph_impact:
                relevant_graph_path = graph_impact[0]['path']

            trace_step = ReasoningTrace(
                step=i+1,
                thought=step_desc,
                status="PASS" if signal.is_safe else "FAIL",
                graph_path=relevant_graph_path
            )
            reasoning_trace.append(trace_step)

            if not signal.is_safe:
                full_reasoning_log.append(f"\n[VALUE FUNCTION HALT] Step {i+1}: {signal.feedback}")
                final_analysis = f"Process halted due to safety violation: {signal.feedback}"
                interrupted = True
                self._log_for_learning(scenario, final_analysis, signal)
                break

        if not interrupted:
            # --- NEW: COMBINED REASONING (Test-Time Compute + Multi-Agent) ---
            # 1. Multi-Agent Red Teaming (Strategic Deliberation)
            full_reasoning_log.append("\n### Phase 2: Multi-Agent 'Red Teaming' (Challenger vs. Defender)")
            debate_result = self.multi_agent_red_team(scenario, checklist)
            
            # 2. Test-Time Compute (Reasoning Scaling)
            # We use the debate as context for a final Best-of-N deliberation
            deliberation_context = f"Debate Summary:\nRED TEAM: {debate_result['red_report'][:200]}...\nBLUE TEAM: {debate_result['blue_report'][:200]}..."
            
            full_reasoning_log.append("\n### Phase 3: Test-Time Compute (Best-of-N Search)")
            deliberation_result = self.deliberate(scenario, checklist + "\n" + deliberation_context, n=3)
            winner = deliberation_result["winner"]
            final_analysis = winner["text"]
            
            full_reasoning_log.append(f"Evaluated 3 reasoning paths. Best Score: {winner['reward_score']}\n" +
                                      f"Winning Path ID: {winner['id']}")
            
            full_reasoning_log.append(f"\n### Phase 4: Final Cortex Analysis\n{final_analysis}")
            
            # Final Steering Check
            steering_signal = self.steering_subsystem.evaluate_recommendation(scenario, final_analysis)
            full_reasoning_log.append(f"\n### Phase 5: Steering Evaluation\n{steering_signal.feedback}")

            if not steering_signal.is_safe:
                if self.model:
                    final_analysis = self._re_reason_with_feedback(checklist, scenario, final_analysis, steering_signal.feedback)
                    full_reasoning_log.append(f"\n### Phase 5: Revised Analysis\n{final_analysis}")
            
            self._log_for_learning(scenario, final_analysis, steering_signal)

        # Artifact Generation
        decision = "FLAGGED"
        if "APPROVED" in final_analysis.upper(): decision = "APPROVED"
        if "DENIED" in final_analysis.upper(): decision = "DENIED"
        
        bullets = [line.strip() for line in final_analysis.split('\n') if line.strip().startswith(('*', '-'))][:3]
        
        card = FlashCardGenerator.generate_decision_card(
            "Neuro-Symbolic Analysis v2",
            decision,
            {"Mode": "Multi-Agent-Steered", "Scaling": "Test-Time-Compute"},
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

    def _re_reason_with_feedback(self, checklist: str, scenario: str, previous_analysis: str, feedback: str) -> str:
        prompt = f"You are a PNC Strategic Advisor. CHECKLIST: {checklist} SCENARIO: {scenario} PREVIOUS ANALYSIS: {previous_analysis} FEEDBACK: {feedback} TASK: Re-analyze strictly adhering to feedback."
        response = self.model.generate_content(prompt)
        return response.text

    def _extract_checklist(self) -> str:
        prompt = f"POLICY: {self.policy_text}\nTASK: Extract First Principles checklist."
        response = self.model.generate_content(prompt)
        return response.text

    def _apply_checklist(self, checklist: str, scenario: str) -> str:
        prompt = f"CHECKLIST: {checklist}\nSCENARIO: {scenario}\nTASK: Analyze against checklist."
        response = self.model.generate_content(prompt)
        return response.text

if __name__ == "__main__":
    engine = S1NeuroSymbolicEngine()
    test_case = "Project 'NeonFuture': 50MW Solar field. Requesting 75% LTV."
    result = engine.process_query(test_case)
    print(json.dumps(result, indent=2))
