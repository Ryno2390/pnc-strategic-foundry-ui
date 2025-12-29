"""
PNC Strategic Foundry - Research: X-Scaling Law Experiment
=========================================================

Hypothesis: In-context sample efficiency is achieved by forcing the 
Student to extract "First Principles" (World Model) rather than 
mimicking tokens (Pattern Matching).

Experiment Case: Green Energy Transition & Grid Storage Lending Policy.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import google.generativeai as genai

# =============================================================================
# CONFIGURATION
# =============================================================================
POLICY_PATH = Path("data/policies/pnc_green_energy_transition_policy.md")
EXAMPLES_PATH = Path("src/backend/research/data/green_energy_examples.json")

# =============================================================================
# EXPERIMENT RUNNER
# =============================================================================
class XScalingExperiment:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def load_data(self):
        with open(POLICY_PATH, "r") as f:
            self.policy_text = f.read()
        
        with open(EXAMPLES_PATH, "r") as f:
            self.examples = json.load(f)

    def run(self, test_scenario: str):
        print("=== Phase 1: First Principles Extraction ===")
        print(f"Loading Policy from: {POLICY_PATH}")
        print(f"Loading {len(self.examples)} Golden Examples...")
        
        # We ask the "Student" to look at the 3 examples and build its own rules
        # Note: We intentionally do NOT feed the full policy text in the prompt 
        # if we want to test 'few-shot induction' purely from examples, 
        # BUT the user's prompt implies the model has *never seen* the policy 
        # and we provide examples. 
        #
        # OPTION A: Pure Induction (No Policy Text, just Examples).
        # OPTION B: Policy + Examples (Standard RAG/Prompting).
        #
        # The user said: "provide S1 with just three 'Golden Examples' of the policy being applied. Instruct S1 to 'Extract the First Principles'..."
        # This implies Induction. However, usually you need the policy text to validly "extract" or at least the examples must be very rich.
        # Let's provide the POLICY TEXT + EXAMPLES and ask it to distill the "Mental Model" or "Checklist".
        
        extraction_prompt = f"""
        You are a Student AI at the PNC Strategic Foundry.
        
        OBJECTIVE: 
        Read the following Banking Policy and 3 'Golden Examples' of its application.
        Your goal is NOT to memorize the text, but to extract the 'First Principles' (The logic) 
        and build a concise 'Reasoning Checklist' that you can use to grade future loan requests.
        
        --- POLICY TEXT ---
        {self.policy_text}
        
        --- GOLDEN EXAMPLES ---
        {json.dumps(self.examples, indent=2)}
        
        TASK:
        1. Identify the Core Invariants (Rules that are never broken).
        2. Create a numbered 'Underwriting Checklist' for this specific policy.
        3. Output ONLY the Checklist.
        """
        
        response = self.model.generate_content(extraction_prompt)
        checklist = response.text
        print("\n--- Student's Internal Checklist (World Model) ---\n")
        print(checklist)

        print("\n=== Phase 2: Zero-Shot Application to New Scenario ===")
        # Now we test the student on a 4th, complex case using its own checklist
        test_prompt = f"""
        You are a PNC Strategic Advisor. You must make a credit decision based ONLY on your Internal Checklist.
        
        INTERNAL CHECKLIST:
        {checklist}
        
        NEW LOAN REQUEST:
        {test_scenario}
        
        TASK:
        1. Analyze the request against each item in your checklist.
        2. Provide a final Decision: APPROVED, DENIED, or FLAGGED (with conditions).
        3. Explain your reasoning.
        """
        
        final_resp = self.model.generate_content(test_prompt)
        print("\n--- Student's Final Decision ---\n")
        print(final_resp.text)

if __name__ == "__main__":
    KEY = os.environ.get("GEMINI_API_KEY")
    if not KEY:
        print("Error: Please set GEMINI_API_KEY environment variable.")
    else:
        # Ensure paths exist relative to script execution or project root
        # Assuming script is run from project root
        if not POLICY_PATH.exists():
            print(f"Error: Policy file not found at {POLICY_PATH}")
        else:
            exp = XScalingExperiment(KEY)
            exp.load_data()
            
            # Scenario 4: The Tricky "Sodium-Ion" Case
            # It has a good PPA and ISA, but uses Tier 2 tech (Sodium-Ion) with Tier 1 leverage (75%).
            tricky_case = (
                "Project 'NeonFuture': 50MW Solar field in Nevada. "
                "12-year PPA with Amazon (AA rated). "
                "The storage component uses new Sodium-Ion batteries to reduce fire risk. "
                "Fully executed ISA with NV Energy. "
                "Requesting 75% LTV to cover the new battery tech costs."
            )
            
            exp.run(tricky_case)