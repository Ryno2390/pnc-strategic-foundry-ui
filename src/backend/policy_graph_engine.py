import re
import json
from pathlib import Path
from typing import List, Dict, Any, Set
from src.backend.policy_engine import PolicyEngine
from src.backend.risk_graph import RiskGraph

class PolicyGraphEngine(PolicyEngine):
    """
    Enhanced Policy Engine that builds a Context Graph during ingestion.
    """

    def __init__(self, persist_dir: str = "./data/policy_index", graph_path: str = "./data/risk_graph.json"):
        super().__init__(persist_dir)
        self.graph = RiskGraph(graph_path)

    def add_policy_files(self, directory: Path):
        """Override to also build the graph."""
        super().add_policy_files(directory)
        
        # Build the graph from the metadata we just generated
        for item in self.metadata:
            self._ingest_into_graph(item)
        
        self.graph.save()
        print(f"Graph updated with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges.")

    def _ingest_into_graph(self, policy_item: Dict[str, Any]):
        """
        Extracts entities and relationships from a policy chunk.
        In a production system, this would use an LLM (Teacher) to perform extraction.
        For this prototype, we use regex/keyword heuristics.
        """
        source_doc = policy_item["source"]
        section_title = policy_item["title"]
        text = policy_item["text"]

        # 1. Create Source Document Node
        doc_id = source_doc.replace(".md", "").upper()
        self.graph.add_node(doc_id, "PolicyDocument", {"filename": source_doc})

        # 2. Create Section Node
        section_id = f"{doc_id}_{policy_item['section_id']}"
        self.graph.add_node(section_id, "PolicySection", {"title": section_title})
        self.graph.add_edge(doc_id, section_id, "HAS_SECTION")

        # 3. Heuristic Extraction of "Requirements" and "Risks"
        # Look for things like "Must", "Minimum", "Required", "Ratio"
        requirement_patterns = {
            "DSCR": r"DSCR (?:of|at least|minimum) ([\d\.]x?)",
            "Credit Score": r"credit score (?:of|minimum) (\d+)",
            "DTI": r"DTI (?:ratio|maximum) (?:of)? (\d+%)",
            "LTV": r"LTV (?:ratio|threshold) (?:of)? (\d+%)"
        }

        for req_name, pattern in requirement_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                req_id = f"REQ_{req_name.upper().replace(' ', '_')}"
                self.graph.add_node(req_id, "Requirement", {
                    "type": req_name,
                    "value": match.group(1),
                    "context": text[:100] + "..."
                })
                self.graph.add_edge(section_id, req_id, "STIPULATES")
                
                # Link requirement to a general Risk node
                risk_id = f"RISK_NON_COMPLIANCE_{req_name.upper().replace(' ', '_')}"
                self.graph.add_node(risk_id, "Risk", {"description": f"Failure to meet {req_name} threshold"})
                self.graph.add_edge(req_id, risk_id, "TRIGGERS_ON_FAILURE")

    def query_graph(self, start_node_id: str, max_depth: int = 5):
        """Helper to query the underlying graph."""
        return self.graph.trace_contagion(start_node_id, max_depth=max_depth)

    def link_entities_to_policies(self, entities_path: Path):
        """
        Links Unified Entities from the Relationship Store to Policies in the Graph.
        This enables "Omnidirectional Inference" (e.g., finding which customers are 
        impacted by a policy change).
        """
        if not entities_path.exists():
            return

        with open(entities_path, "r") as f:
            entities = json.load(f)

        for entity in entities:
            ent_id = entity["unified_id"]
            ent_name = entity["canonical_name"]
            ent_type = entity["entity_type"]

            # Add Entity node to Risk Graph
            self.graph.add_node(ent_id, "Entity", {
                "name": ent_name,
                "type": ent_type
            })

            # Heuristic: Link Businesses to SBA Policy
            if ent_type == "BUSINESS":
                self.graph.add_edge(ent_id, "SBA_7A_LOAN_POLICY", "SUBJECT_TO")
            
            # Heuristic: Link People in Wealth Management to generic policies
            if any(s["source"] == "WEALTH_ADVISORY" for s in entity.get("source_records", [])):
                 self.graph.add_edge(ent_id, "RESIDENTIAL_MORTGAGE_POLICY", "SUBJECT_TO")

        self.graph.save()
        print(f"Linked {len(entities)} entities to the Risk Graph.")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    policy_dir = project_root / "data" / "policies"
    entities_file = project_root / "data" / "relationship_store" / "resolved" / "unified_entities.json"
    
    engine = PolicyGraphEngine(
        persist_dir=str(project_root / "data" / "policy_index"),
        graph_path=str(project_root / "data" / "risk_graph.json")
    )
    engine.add_policy_files(policy_dir)
    engine.link_entities_to_policies(entities_file)
    
    # Test query: Risk Contagion from a Customer
    print("\n--- Testing Risk Contagion (Customer -> Policy -> Risk) ---")
    # UNI-0042 is JOHNSON VENTURES LLC
    results = engine.query_graph("UNI-0042")
    for r in results:
        if r['type'] == "Risk":
            print(f"IMPACTED RISK: {r['node_id']} (Depth: {r['depth']})")
            print(f"  Trace: {' -> '.join(r['path'])}")
