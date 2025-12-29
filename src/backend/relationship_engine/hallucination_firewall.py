"""
PNC Strategic Foundry - Hallucination Firewall (CoVe)
=====================================================
Implements Chain-of-Verification (CoVe) to minimize hallucinations.

Architecture:
1.  **Draft:** Generate baseline response.
2.  **Verify:** Generate verification questions based on the draft.
3.  **Execute:** Answer questions using ONLY the source context.
4.  **Revise:** Rewrite the draft if verification fails.

This acts as the "Subconscious Editor" for the Advisor.
"""

import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PNC.HallucinationFirewall")

@dataclass
class VerificationResult:
    is_safe: bool
    original_draft: str
    revised_response: str
    corrections_made: List[str]
    verification_score: float # 0.0 to 1.0

class ChainOfVerification:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            logger.warning("No API Key. Firewall disabled (Pass-through mode).")
            self.model = None

    def verify_response(self, query: str, context: str, draft_response: str) -> VerificationResult:
        """
        Main entry point: Audits the draft response against the context.
        """
        if not self.model:
            return VerificationResult(True, draft_response, draft_response, [], 1.0)

        # Step 1: Generate Verification Questions
        questions = self._generate_verification_questions(draft_response)
        
        if not questions:
            return VerificationResult(True, draft_response, draft_response, [], 1.0)

        # Step 2: Execute Verification (Answer questions using ONLY context)
        verification_report = self._execute_verification(questions, context)
        
        # Step 3: Check for Hallucinations & Revise
        revision = self._revise_response(query, draft_response, verification_report)
        
        return revision

    def _generate_verification_questions(self, draft: str) -> List[str]:
        """
        Ask the model to identify factual claims that need checking.
        """
        prompt = f"""
        You are a Fact-Checking Editor.
        
        DRAFT TEXT:
        \"{draft}\" # Corrected escaping for triple quotes within f-string
        
        TASK:
        Identify factual claims in the text (numbers, policy rules, entities, dates).
        Generate 3-5 short, specific questions to verify these claims.
        Example: \"Does the policy allow 80% LTV?\" or \"Is the minimum PPA term 10 years?\"
        
        OUTPUT JSON ONLY:
        {{
            "questions": ["Question 1", "Question 2"]
        }}
        """
        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            return data.get("questions", [])
        except Exception as e:
            logger.error(f"Failed to generate verification questions: {e}")
            return []

    def _execute_verification(self, questions: List[str], context: str) -> str:
        """
        Answer the verification questions using ONLY the provided context.
        """
        prompt = f"""
        You are an Objective Auditor.
        
        SOURCE CONTEXT (The only truth):
        {context}
        
        QUESTIONS:
        {json.dumps(questions)}
        
        TASK:
        Answer each question based strictly on the SOURCE CONTEXT. 
        If the context does not contain the answer, say "Not found in context".
        Do not use outside knowledge.
        
        OUTPUT FORMAT:
        Q: [Question]
        A: [Answer]
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Failed to execute verification: {e}")
            return "Verification Failed."

    def _revise_response(self, query: str, draft: str, verification_report: str) -> VerificationResult:
        """
        Rewrite the draft if the verification report shows discrepancies.
        """
        prompt = f"""
        You are the Final Editor.
        
        USER QUERY: {query}
        ORIGINAL DRAFT: {draft}
        VERIFICATION REPORT (Fact-Check):
        {verification_report}
        
        TASK:
        1. Compare the Draft against the Verification Report.
        2. Identify any hallucinations (claims in Draft that are contradicted or unsupported by Report).
        3. Rewrite the response to be 100% faithful to the Verification Report.
        4. List specific corrections made.
        
        OUTPUT JSON ONLY:
        {{
            "revised_response": "The corrected text...",
            "corrections": ["Changed LTV from 80% to 50%", "Removed claim about X"],
            "score": 0.0 to 1.0 (1.0 = Original was perfect)
        }}
        """
        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            
            return VerificationResult(
                is_safe=data.get("score", 0.0) > 0.9,
                original_draft=draft,
                revised_response=data.get("revised_response", draft),
                corrections_made=data.get("corrections", []),
                verification_score=data.get("score", 0.0)
            )
        except Exception as e:
            logger.error(f"Failed to revise response: {e}")
            return VerificationResult(False, draft, draft, ["Error in revision"], 0.0)

if __name__ == "__main__":
    # Test the Firewall
    firewall = ChainOfVerification()
    
    # Scenario: Model hallucinates a 90% LTV when policy says 80%
    ctx = "Policy CIB-RE-2025: Maximum LTV for Solar projects is 80%. Minimum PPA term is 10 years."
    bad_draft = "Based on the policy, your Solar project is approved for 90% LTV because it has a 12-year PPA."
    
    print("--- Testing Hallucination Firewall ---")
    print(f"Context: {ctx}")
    print(f"Draft:   {bad_draft}\n")
    
    result = firewall.verify_response("What is the max LTV?", ctx, bad_draft)
    
    print(f"Score: {result.verification_score}")
    print(f"Corrections: {result.corrections_made}")
    print(f"Final Response: {result.revised_response}")