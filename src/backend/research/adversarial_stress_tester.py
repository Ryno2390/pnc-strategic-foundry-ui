"""
PNC Strategic Foundry - Adversarial Policy Stress Tester
======================================================
Implements an "Active Learning" loop where an Adversarial Teacher
generates specific edge-case scenarios to test the S1 Student's
grasp of "First Principles".

Flow:
1. Teacher (Generator): Creates a deceptive loan scenario (High Signal, 1 Fatal Flaw).
2. Student (S1): Analyzes the scenario using its Internal Checklist.
3. Judge: Compares Student's decision vs. Teacher's Ground Truth.
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List
import google.generativeai as genai

# Add project root to sys.path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.relationship_engine.s1_neuro_symbolic import S1NeuroSymbolicEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("PNC.Adversarial")

class AdversarialTeacher:
    def __init__(self, api_key: str, policy_text: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.policy_text = policy_text

    def generate_trick_scenario(self, difficulty: str = "HARD") -> Dict[str, str]:
        """
        Generates a scenario designed to trick the student.
        It should look like an APPROVAL but actually be a DENIAL/FLAG.
        """
        prompt = f"""
        You are a Senior Credit Risk Trainer. Your goal is to test a Junior Analyst (AI).
        
        POLICY:
        {self.policy_text}
        
        TASK:
        Generate a 'Trick Scenario' for a Green Energy loan.
        1. The scenario should look VERY POSITIVE (e.g., Apple/Microsoft as off-taker, experienced developers).
        2. However, insert EXACTLY ONE subtle violation of the policy (e.g., using Tier 2 tech but asking for Tier 1 LTV, or missing the wetland permit, or too much merchant revenue).
        3. The violation should be specific and factual, not vague.
        
        OUTPUT JSON ONLY:
        {{
            "scenario": "The full scenario description...",
            "expected_decision": "DENIED" or "FLAGGED",
            "violation_type": "LTV / Tech Risk / Revenue / etc.",
            "explanation": "Why this must be rejected despite the positive signals."
        }}
        """
        
        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            
            # Handle case where LLM returns a list of scenarios instead of one
            if isinstance(data, list):
                if len(data) > 0:
                    return data[0]
                else:
                    return None
            return data
        except Exception as e:
            logger.error(f"Teacher failed to generate: {e}")
            return None

class StressTestRunner:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required.")
        
        # Load Policy
        self.policy_path = Path("data/policies/pnc_green_energy_transition_policy.md")
        with open(self.policy_path, "r") as f:
            self.policy_text = f.read()

        # Initialize Agents
        self.teacher = AdversarialTeacher(self.api_key, self.policy_text)
        self.student = S1NeuroSymbolicEngine(self.api_key)

    def run_round(self, round_id: int):
        print(f"\n{'='*60}")
        print(f"ROUND {round_id}: The Adversarial Challenge")
        print(f"{'='*60}")

        # 1. Teacher Generates
        print("👨‍🏫 TEACHER: Generating a tricky edge case...")
        case = self.teacher.generate_trick_scenario()
        if not case:
            print("Teacher failed. Skipping round.")
            return

        print(f"\n📜 SCENARIO:\n{case['scenario']}")
        print(f"\n🎯 TRAP SET: Expecting {case['expected_decision']} due to {case['violation_type']}")
        
        # 2. Student Analyzes
        print("\n🤖 STUDENT: Analyzing with Neuro-Symbolic Engine...")
        start_time = time.time()
        result = self.student.process_query(case['scenario'])
        duration = time.time() - start_time
        
        student_response = result.get("response", "")
        
        # 3. Judgment
        print(f"\n⏱️  Thinking Time: {duration:.2f}s")
        print(f"📝 STUDENT DECISION:\n{student_response[:300]}...\n[truncated]")
        
        # Simple string matching for verdict
        student_verdict = "UNKNOWN"
        if "APPROVED" in student_response.upper():
            student_verdict = "APPROVED"
        if "DENIED" in student_response.upper() or "DENY" in student_response.upper():
            student_verdict = "DENIED"
        if "FLAGGED" in student_response.upper() or "FLAG" in student_response.upper():
            student_verdict = "FLAGGED"

        expected = case['expected_decision'].upper()
        
        # Fuzzy match for FLAGGED/DENIED overlap (often interchangeable in risk)
        success = False
        if expected in student_verdict:
            success = True
        elif (expected == "DENIED" or expected == "FLAGGED") and (student_verdict == "DENIED" or student_verdict == "FLAGGED"):
             success = True # Treat Flag/Deny as "Catching the issue"

        if success:
            print(f"\n✅ PASS: Student caught the trap! ({case['violation_type']})")
        else:
            print(f"\n❌ FAIL: Student fell for it. Verdict: {student_verdict}, Expected: {expected}")

if __name__ == "__main__":
    runner = StressTestRunner()
    # Run 3 adversarial rounds
    for i in range(1, 4):
        runner.run_round(i)
