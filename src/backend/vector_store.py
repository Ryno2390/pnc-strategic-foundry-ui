import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

class RelationshipVectorStore:
    """
    Vector database wrapper for the Relationship Store.
    Foundation for Pillar 3: Knowledge Expansion (RAG).
    """

    def __init__(self, persist_directory: str = "./data/vector_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(self.persist_directory)
        ))
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="pnc_relationships",
            metadata={"description": "Unified entity graph for PNC Strategic Foundry"}
        )

    def index_entities(self, entities_path: Path):
        """Index unified entities from JSON file."""
        if not entities_path.exists():
            print(f"Error: {entities_path} not found")
            return

        with open(entities_path, "r") as f:
            entities = json.load(f)

        documents = []
        metadatas = []
        ids = []

        for entity in entities:
            # Create a rich text description for semantic search
            desc = f"Entity: {entity['canonical_name']}\nType: {entity['entity_type']}\n"
            
            if entity.get("tax_id_last4"):
                desc += f"Tax ID (Last 4): {entity['tax_id_last4']}\n"
            
            if entity.get("emails"):
                desc += f"Emails: {', '.join(entity['emails'])}\n"
            
            if entity.get("phones"):
                desc += f"Phones: {', '.join(entity['phones'])}\n"

            # Add source system info
            sources = [s['source'] for s in entity.get('source_records', [])]
            desc += f"Systems: {', '.join(sources)}\n"

            documents.append(desc)
            metadatas.append({
                "name": entity['canonical_name'],
                "type": entity['entity_type'],
                "unified_id": entity['unified_id'],
                "sources": ",".join(sources)
            })
            ids.append(entity['unified_id'])

        # Add to collection in batches
        if ids:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Indexed {len(ids)} entities into vector store.")

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Semantic search for entities."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results
        output = []
        for i in range(len(results['ids'][0])):
            output.append({
                "id": results['ids'][0][i],
                "name": results['metadatas'][0][i]['name'],
                "score": results['distances'][0][i],
                "description": results['documents'][0][i],
                "metadata": results['metadatas'][0][i]
            })
        return output

    def persist(self):
        """Persist the database to disk."""
        self.client.persist()

if __name__ == "__main__":
    # Test the vector store
    project_root = Path(__file__).parent.parent.parent
    entities_file = project_root / "data" / "relationship_store" / "resolved" / "unified_entities.json"
    
    store = RelationshipVectorStore(str(project_root / "data" / "vector_db"))
    store.index_entities(entities_file)
    
    print("\n--- Testing Semantic Search ---")
    query = "Who is connected to wealth management and lives in Fox Chapel?"
    results = store.search(query, n_results=2)
    
    for r in results:
        print(f"Match: {r['name']} (ID: {r['id']}, Score: {r['score']:.4f})")
        print(f"Details: {r['metadata']['sources']}")
        print("-" * 20)
    
    store.persist()
