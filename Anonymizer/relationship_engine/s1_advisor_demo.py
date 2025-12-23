"""
PNC Strategic Foundry - S1 Advisor End-to-End Demo
====================================================
Demonstrates the complete pipeline:
    Query → S1 Reasoning → Tool Call → Context Assembly → Response

This shows how S1 can use the relationship store to provide
comprehensive, customer-centered answers to advisor queries.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from relationship_engine.context_assembler import (
    ContextAssembler,
    execute_tool,
    AVAILABLE_TOOLS
)

# ============================================================================
# S1 REASONING TRACE FORMAT
# ============================================================================

@dataclass
class ReasoningStep:
    """A single step in S1's reasoning trace."""
    step_number: int
    thought: str
    action: Optional[str] = None
    tool_call: Optional[Dict] = None
    tool_result: Optional[Any] = None
    observation: Optional[str] = None

class S1ReasoningEngine:
    """
    Simulates the S1 Reasoning Model with tool-use capability.

    In production, this would be the fine-tuned Qwen model with
    tool-use prompts. For this demo, we simulate the reasoning
    process to show the complete flow.
    """

    def __init__(self):
        self.assembler = ContextAssembler()
        self.reasoning_trace: List[ReasoningStep] = []
        self.step_count = 0

    def _add_step(self, thought: str, action: str = None,
                  tool_call: Dict = None, tool_result: Any = None,
                  observation: str = None) -> ReasoningStep:
        """Add a step to the reasoning trace."""
        self.step_count += 1
        step = ReasoningStep(
            step_number=self.step_count,
            thought=thought,
            action=action,
            tool_call=tool_call,
            tool_result=tool_result,
            observation=observation
        )
        self.reasoning_trace.append(step)
        return step

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process an advisor query using reasoning + tool-use.

        Returns the complete response with reasoning trace.
        """
        self.reasoning_trace = []
        self.step_count = 0

        # Step 1: Parse and understand the query
        self._add_step(
            thought=f"I received an advisor query: '{query}'. "
                    f"Let me analyze what information is needed to answer this."
        )

        # Step 2: Identify the entities and data needed
        entities_needed = self._extract_entities(query)
        data_type = self._identify_data_type(query)

        self._add_step(
            thought=f"This query is asking about {data_type}. "
                    f"I identified these entities: {entities_needed}. "
                    f"I need to use my tools to look up this information."
        )

        # Step 3: Determine which tool to call
        if "household" in query.lower() or "family" in query.lower():
            tool_name = "get_household_summary"
            household_name = self._extract_household_name(query)

            self._add_step(
                thought=f"Since this is a household-level query, I should use "
                        f"the get_household_summary tool to get aggregated data "
                        f"for the '{household_name}' household.",
                action="Call get_household_summary tool"
            )

            # Execute tool call
            tool_result = execute_tool(tool_name, household_name=household_name)

            self._add_step(
                thought="Executing tool call...",
                tool_call={"tool": tool_name, "params": {"household_name": household_name}},
                tool_result=tool_result,
                observation=f"Retrieved data for {len(tool_result.get('members', []))} "
                           f"household members with total relationship value of "
                           f"${tool_result.get('totals', {}).get('total_relationship_value', 0):,.2f}"
            )

        elif "customer" in query.lower() or any(name in query.lower() for name in ["john", "jane", "robert"]):
            tool_name = "get_customer_360"
            entity_name = entities_needed[0] if entities_needed else "Unknown"

            self._add_step(
                thought=f"This is a customer-specific query. I should use "
                        f"the get_customer_360 tool to get complete information "
                        f"for '{entity_name}'.",
                action="Call get_customer_360 tool"
            )

            # Execute tool call
            tool_result = execute_tool(tool_name, entity_id_or_name=entity_name)

            self._add_step(
                thought="Executing tool call...",
                tool_call={"tool": tool_name, "params": {"entity_id_or_name": entity_name}},
                tool_result=tool_result,
                observation=f"Retrieved Customer 360 data including "
                           f"{len(tool_result.get('personal_accounts', []))} accounts and "
                           f"{len(tool_result.get('business_connections', []))} business connections"
            )

        else:
            # Default search
            tool_name = "search_entities"
            search_query = " ".join(entities_needed) if entities_needed else query

            self._add_step(
                thought=f"I need to search for entities matching '{search_query}'.",
                action="Call search_entities tool"
            )

            tool_result = execute_tool(tool_name, query=search_query)

            self._add_step(
                thought="Executing search...",
                tool_call={"tool": tool_name, "params": {"query": search_query}},
                tool_result=tool_result,
                observation=f"Found {len(tool_result)} matching entities"
            )

        # Step 4: Synthesize the response
        final_response = self._generate_response(query, tool_result, data_type)

        self._add_step(
            thought="I have all the information needed. Let me synthesize a "
                    "comprehensive response for the advisor.",
            action="Generate final response"
        )

        return {
            "query": query,
            "response": final_response,
            "reasoning_trace": [
                {
                    "step": s.step_number,
                    "thought": s.thought,
                    "action": s.action,
                    "tool_call": s.tool_call,
                    "observation": s.observation
                }
                for s in self.reasoning_trace
            ],
            "tool_data": tool_result,
            "timestamp": datetime.now().isoformat()
        }

    def _extract_entities(self, query: str) -> List[str]:
        """Extract entity names from the query."""
        # Simple extraction - in production, use NER
        entities = []
        known_names = ["Smith", "Johnson", "Chen", "O'Brien", "Garcia", "Torres"]
        for name in known_names:
            if name.lower() in query.lower():
                entities.append(name)
        return entities

    def _extract_household_name(self, query: str) -> str:
        """Extract household/family name from query."""
        entities = self._extract_entities(query)
        return entities[0] if entities else "Unknown"

    def _identify_data_type(self, query: str) -> str:
        """Identify what type of data the query is asking about."""
        query_lower = query.lower()
        if "total" in query_lower and ("value" in query_lower or "relationship" in query_lower):
            return "total relationship value"
        elif "account" in query_lower:
            return "account information"
        elif "business" in query_lower:
            return "business connections"
        elif "portfolio" in query_lower or "investment" in query_lower:
            return "investment portfolios"
        else:
            return "comprehensive relationship data"

    def _generate_response(self, query: str, tool_result: Dict, data_type: str) -> str:
        """Generate the final natural language response."""
        if "members" in tool_result:  # Household summary result
            members = tool_result.get("members", [])
            totals = tool_result.get("totals", {})
            businesses = tool_result.get("connected_businesses", [])

            response = f"""Based on my analysis of the PNC relationship data:

**{tool_result.get('household_name', 'Unknown').upper()} HOUSEHOLD SUMMARY**

**Members ({len(members)}):**
"""
            for m in members:
                response += f"  • {m['name']}: ${m['personal_aum']:,.2f} in personal assets ({m['accounts_count']} accounts)\n"

            if businesses:
                response += f"\n**Connected Businesses ({len(businesses)}):**\n"
                for b in businesses:
                    response += f"  • {b['name']} ({b['role']}, {b['ownership_pct']}% ownership)\n"

            response += f"""
**FINANCIAL TOTALS:**
  • Personal AUM:        ${totals.get('personal_aum', 0):>15,.2f}
  • Business Exposure:   ${totals.get('business_exposure', 0):>15,.2f}
  ────────────────────────────────────────
  • **TOTAL RELATIONSHIP VALUE: ${totals.get('total_relationship_value', 0):>12,.2f}**

**Advisor Insight:** The Smith household represents a significant Private Banking relationship
with cross-LOB touchpoints in Consumer, Wealth Management, and Commercial Banking. Consider
discussing consolidated reporting and potential 529 plan optimization given the business cash flow.
"""
            return response

        elif "canonical_name" in tool_result:  # Customer 360 result
            name = tool_result.get("canonical_name", "Unknown")
            response = f"""**CUSTOMER 360: {name}**

**Personal Accounts:** {len(tool_result.get('personal_accounts', []))}
**Wealth Portfolios:** {len(tool_result.get('wealth_portfolios', []))}
**Household Members:** {len(tool_result.get('household_members', []))}
**Business Connections:** {len(tool_result.get('business_connections', []))}

**Total Relationship Value:** ${tool_result.get('total_relationship_value', 0):,.2f}
"""
            return response

        else:
            return f"Retrieved {len(tool_result) if isinstance(tool_result, list) else 1} results for your query."


# ============================================================================
# DEMO EXECUTION
# ============================================================================

def print_reasoning_trace(result: Dict):
    """Print the reasoning trace in a readable format."""
    print("\n" + "═" * 80)
    print("S1 REASONING TRACE")
    print("═" * 80)

    for step in result.get("reasoning_trace", []):
        print(f"\n┌─ Step {step['step']}")
        print(f"│ 💭 Thought: {step['thought']}")
        if step.get('action'):
            print(f"│ ⚡ Action: {step['action']}")
        if step.get('tool_call'):
            print(f"│ 🔧 Tool Call: {step['tool_call']['tool']}({step['tool_call']['params']})")
        if step.get('observation'):
            print(f"│ 👁️ Observation: {step['observation']}")
        print("└" + "─" * 60)


def run_demo():
    """Run the end-to-end demo."""
    print("=" * 80)
    print("PNC STRATEGIC FOUNDRY - S1 ADVISOR END-TO-END DEMO")
    print("=" * 80)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis demo shows the complete pipeline:")
    print("  Query → S1 Reasoning → Tool Call → Context Assembly → Response")

    # Initialize S1 engine
    s1 = S1ReasoningEngine()

    # Demo Query
    query = "What is the total relationship value for the Smith household?"

    print("\n" + "─" * 80)
    print("ADVISOR QUERY")
    print("─" * 80)
    print(f"\n📝 \"{query}\"")

    # Process the query
    result = s1.process_query(query)

    # Print reasoning trace
    print_reasoning_trace(result)

    # Print final response
    print("\n" + "═" * 80)
    print("S1 ADVISOR RESPONSE")
    print("═" * 80)
    print(result["response"])

    # Print raw tool data for transparency
    print("\n" + "─" * 80)
    print("RAW TOOL DATA (for verification)")
    print("─" * 80)
    tool_data = result.get("tool_data", {})
    if "members" in tool_data:
        print(f"\nHousehold: {tool_data.get('household_name')}")
        print(f"Members: {[m['name'] for m in tool_data.get('members', [])]}")
        print(f"Totals: {json.dumps(tool_data.get('totals', {}), indent=2)}")

    # Additional demo queries
    print("\n" + "═" * 80)
    print("ADDITIONAL DEMO QUERIES")
    print("═" * 80)

    additional_queries = [
        "Tell me about customer William Chen",
        "What businesses are connected to the Johnson family?"
    ]

    for q in additional_queries:
        print(f"\n📝 Query: \"{q}\"")
        print("─" * 60)
        result = s1.process_query(q)

        # Show abbreviated trace
        print(f"   🔧 Tool Used: {result['reasoning_trace'][-2]['tool_call']['tool'] if len(result['reasoning_trace']) > 1 and result['reasoning_trace'][-2].get('tool_call') else 'N/A'}")

        # Show response preview
        response_preview = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
        print(f"   📤 Response Preview: {response_preview.split(chr(10))[0]}")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("""
The S1 Reasoning Model successfully:
  ✅ Parsed the natural language query
  ✅ Identified the relevant tool to call
  ✅ Retrieved data from the Relationship Store
  ✅ Synthesized a comprehensive advisor response

This demonstrates the complete "Brain + Memory + Bridge" architecture
where S1 can reason over unified customer data across all LOBs.
""")


if __name__ == "__main__":
    run_demo()
