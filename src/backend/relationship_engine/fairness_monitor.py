"""
PNC Strategic Foundry - Prohibited Factor Monitor (Fairness & Bias)
==================================================================

Operationalizes Fair Lending requirements by scanning AI reasoning traces 
for prohibited factors (Race, Gender, Religion, etc.) or their high-risk 
proxies (Zip Code, Neighborhood names).

Prevents "Proxy Discrimination" before the advisor sees the AI output.
"""

from typing import List, Dict, Any, Tuple
import re

class FairnessMonitor:
    """
    Real-time scanner for bias and prohibited factors.
    """

    # Prohibited Factors (Equal Credit Opportunity Act)
    PROHIBITED_FACTORS = [
        "race", "color", "religion", "national origin", "sex", 
        "marital status", "age", "public assistance", "sexual orientation",
        "gender identity", "ethnicity"
    ]

    # Common Proxies for Protected Classes (High Risk)
    PROXY_FACTORS = [
        "zip code", "neighborhood", "area code", "census tract",
        "redline", "low-income area", "gentrification"
    ]

    def __init__(self, custom_keywords: List[str] = None):
        self.keywords = self.PROHIBITED_FACTORS + self.PROXY_FACTORS
        if custom_keywords:
            self.keywords.extend(custom_keywords)
            
        # Compile regex for performance
        pattern = r"\b(" + "|".join(re.escape(k) for k in self.keywords) + r")\b"
        self.regex = re.compile(pattern, re.IGNORECASE)

    def scan_trace(self, text: str) -> Tuple[bool, List[str]]:
        """
        Scans a reasoning trace or message for prohibited keywords.
        Returns (is_flagged, found_keywords).
        """
        matches = self.regex.findall(text)
        if matches:
            # deduplicate and return
            return True, list(set(m.lower() for m in matches))
        
        return False, []

    def sanitize_trace(self, text: str) -> str:
        """
        Replaces prohibited factors with [REDACTED_FOR_FAIRNESS].
        """
        return self.regex.sub("[REDACTED_FOR_FAIRNESS]", text)

if __name__ == "__main__":
    monitor = FairnessMonitor()
    
    test_trace = "The client lives in a low-income zip code which might indicate high risk."
    flagged, words = monitor.scan_trace(test_trace)
    
    print(f"Text: {test_trace}")
    print(f"Flagged: {flagged}, Keywords: {words}")
    print(f"Sanitized: {monitor.sanitize_trace(test_trace)}")
