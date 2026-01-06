import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

class RiskGraph:
    """
    Pillar 4: Context Graph (Relational Logic).
    Maps relationships between Policies, Entities, and Risks.
    Provides "Graph Traversal" for Risk Contagion analysis.
    """

    def __init__(self, persist_path: str = "./data/risk_graph.json"):
        self.persist_path = Path(persist_path)
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, str]] = []
        
        if self.persist_path.exists():
            self.load()

    def add_node(self, node_id: str, node_type: str, properties: Dict[str, Any] = None):
        """Adds a node to the graph."""
        self.nodes[node_id] = {
            "type": node_type,
            "properties": properties or {}
        }

    def add_edge(self, source: str, target: str, rel_type: str):
        """Adds a directed edge between two nodes."""
        if source not in self.nodes or target not in self.nodes:
            # We allow adding edges for nodes that don't exist yet in this prototype,
            # but ideally, we'd log a warning or create a placeholder.
            pass
        
        edge = {
            "source": source,
            "target": target,
            "rel_type": rel_type
        }
        if edge not in self.edges:
            self.edges.append(edge)

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """Finds all neighbors of a node."""
        neighbors = []
        for edge in self.edges:
            if direction in ["out", "both"] and edge["source"] == node_id:
                neighbors.append({
                    "node_id": edge["target"],
                    "rel_type": edge["rel_type"],
                    "direction": "out"
                })
            if direction in ["in", "both"] and edge["target"] == node_id:
                neighbors.append({
                    "node_id": edge["source"],
                    "rel_type": edge["rel_type"],
                    "direction": "in"
                })
        return neighbors

    def trace_contagion(self, start_node_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Performs a Breadth-First Search to find all nodes impacted by a risk.
        Useful for "Risk Contagion" mapping.
        """
        visited = {start_node_id}
        queue = [(start_node_id, 0, [])]
        results = []

        while queue:
            current_id, depth, path = queue.pop(0)
            
            if depth > 0:
                results.append({
                    "node_id": current_id,
                    "type": self.nodes.get(current_id, {}).get("type", "Unknown"),
                    "depth": depth,
                    "path": path
                })

            if depth < max_depth:
                for neighbor in self.get_neighbors(current_id, direction="out"):
                    if neighbor["node_id"] not in visited:
                        visited.add(neighbor["node_id"])
                        new_path = path + [f"{current_id} --({neighbor['rel_type']})--> {neighbor['node_id']}"]
                        queue.append((neighbor["node_id"], depth + 1, new_path))
        
        return results

    def save(self):
        """Persists the graph to JSON."""
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "w") as f:
            json.dump({
                "nodes": self.nodes,
                "edges": self.edges
            }, f, indent=2)

    def load(self):
        """Loads the graph from JSON."""
        with open(self.persist_path, "r") as f:
            data = json.load(f)
            self.nodes = data.get("nodes", {})
            self.edges = data.get("edges", [])

if __name__ == "__main__":
    # Test Graph
    graph = RiskGraph()
    
    # 1. Add Nodes
    graph.add_node("SBA_7A_POLICY", "Policy", {"title": "SBA 7(a) Guidelines"})
    graph.add_node("DSCR_REQUIREMENT", "Requirement", {"threshold": 1.25})
    graph.add_node("COMPLIANCE_RISK", "Risk", {"severity": "High"})
    graph.add_node("CUSTOMER_ENTITY_001", "Entity", {"name": "Acme Services"})
    
    # 2. Add Relationships
    graph.add_edge("SBA_7A_POLICY", "DSCR_REQUIREMENT", "CONTAINS")
    graph.add_edge("DSCR_REQUIREMENT", "COMPLIANCE_RISK", "TRIGGERS_ON_FAILURE")
    graph.add_edge("CUSTOMER_ENTITY_001", "SBA_7A_POLICY", "SUBJECT_TO")
    
    # 3. Test Contagion
    print("Tracing Risk Contagion from CUSTOMER_ENTITY_001:")
    impact = graph.trace_contagion("CUSTOMER_ENTITY_001")
    for node in impact:
        print(f"Depth {node['depth']}: {node['node_id']} ({node['type']})")
        print(f"  Path: {' -> '.join(node['path'])}")
    
    graph.save()
