import os
import json
from pathlib import Path
from typing import List, Dict, Any
import re

class PolicyEngine:
    """
    Knowledge Pillar: Policy Search Engine (Lightweight Prototype).
    Uses keyword-based scoring to find relevant policy snippets.
    """

    def __init__(self, persist_dir: str = "./data/policy_index"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.persist_dir / "policy_metadata.json"
        self.metadata = []

        if self.meta_path.exists():
            self.load()

    def add_policy_files(self, directory: Path):
        """Read, chunk, and index all policy files in a directory."""
        if not directory.exists():
            print(f"Error: {directory} not found")
            return

        self.metadata = []
        for file_path in directory.glob("*.md"):
            with open(file_path, "r") as f:
                content = f.read()
            
            # Simple chunking by section
            chunks = content.split("##")
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                
                clean_chunk = chunk.strip()
                if i > 0:
                    clean_chunk = "## " + clean_chunk
                
                # Get the title (first line)
                title = clean_chunk.split("\n")[0].replace("#", "").strip()

                self.metadata.append({
                    "title": title,
                    "text": clean_chunk,
                    "source": file_path.name,
                    "section_id": i,
                    "keywords": self._extract_keywords(clean_chunk)
                })
        
        self.save()
        print(f"Indexed {len(self.metadata)} sections from {directory}")

    def _extract_keywords(self, text: str) -> Set[str]:
        # Simple keyword extraction: lowercase words > 3 chars
        words = re.findall(r'\w+', text.lower())
        return {w for w in words if len(w) > 3}

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Keyword-based search for relevant policy snippets."""
        if not self.metadata:
            return []

        query_keywords = self._extract_keywords(query)
        scored_results = []

        for item in self.metadata:
            # Score based on keyword overlap
            overlap = query_keywords.intersection(item["keywords"])
            score = len(overlap)
            
            # Bonus for title match
            title_keywords = self._extract_keywords(item["title"])
            title_overlap = query_keywords.intersection(title_keywords)
            score += len(title_overlap) * 2

            if score > 0:
                scored_results.append((score, item))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, item in scored_results[:top_k]:
            results.append({
                "text": item["text"],
                "source": item["source"],
                "score": float(score),
                "title": item["title"]
            })
        return results

    def save(self):
        # Convert set to list for JSON serialization
        save_data = []
        for item in self.metadata:
            d = item.copy()
            d["keywords"] = list(d["keywords"])
            save_data.append(d)
            
        with open(self.meta_path, "w") as f:
            json.dump(save_data, f, indent=2)

    def load(self):
        with open(self.meta_path, "r") as f:
            load_data = json.load(f)
            
        self.metadata = []
        for item in load_data:
            item["keywords"] = set(item["keywords"])
            self.metadata.append(item)

if __name__ == "__main__":
    from typing import Set # Needed for type hint in refactored code
    # Test the policy engine
    project_root = Path(__file__).parent.parent.parent
    policy_dir = project_root / "data" / "policies"
    
    engine = PolicyEngine(persist_dir=str(project_root / "data" / "policy_index"))
    engine.add_policy_files(policy_dir)
    
    print("\n--- Testing Policy Search ---")
    query = "What are the DSCR requirements for an SBA loan?"
    results = engine.search(query, top_k=1)
    
    if results:
        print(f"Found in {results[0]['source']} (Score: {results[0]['score']}):")
        print(results[0]['text'])
    else:
        print("No results found.")
