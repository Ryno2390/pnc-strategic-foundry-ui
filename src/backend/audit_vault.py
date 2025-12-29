import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("AuditVault")

class AuditVault:
    """
    Immutable Audit Vault for Regulatory Compliance. 
    
    Implements a cryptographic hash chain (similar to a blockchain) where 
    each record contains the hash of the previous record. This ensures 
    that reasoning traces cannot be modified or deleted without 
    breaking the chain integrity. 
    
    Compliance: SEC Rule 17a-4, OCC AI Guidance.
    """

    def __init__(self, storage_path: str = "./data/audit_log.jsonl"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize file if not exists
        if not self.storage_path.exists():
            self.storage_path.touch()

    def _get_last_hash(self) -> str:
        """Retrieve the hash of the last record in the log."""
        if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
            return "GENESIS"
        
        last_line = ""
        with open(self.storage_path, "rb") as f:
            # Seek to the end and find the last line
            f.seek(0, 2)
            if f.tell() == 0:
                return "GENESIS"
            
            f.seek(-2, 2)
            while f.read(1) != b"\n":
                f.seek(-2, 1)
                if f.tell() == 0:
                    break
            last_line = f.readline().decode().strip()
        
        if not last_line:
            return "GENESIS"
            
        try:
            return json.loads(last_line).get("record_hash", "ERROR")
        except json.JSONDecodeError:
            return "ERROR"

    def log_event(
        self, 
        advisor_id: str, 
        query: str, 
        reasoning_trace: List[Dict], 
        response: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log a complete reasoning event with cryptographic integrity.
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        previous_hash = self._get_last_hash()
        
        # Construct record for hashing (excluding the hash field itself)
        record = {
            "timestamp": timestamp,
            "advisor_id": advisor_id,
            "query": query,
            "query_hash": hashlib.sha256(query.encode()).hexdigest(),
            "reasoning_trace": reasoning_trace,
            "response": response,
            "response_hash": hashlib.sha256(response.encode()).hexdigest(),
            "metadata": metadata or {},
            "previous_hash": previous_hash
        }
        
        # Calculate current record hash
        record_json = json.dumps(record, sort_keys=True)
        record_hash = hashlib.sha256(record_json.encode()).hexdigest()
        record["record_hash"] = record_hash
        
        # Append to log
        with open(self.storage_path, "a") as f:
            f.write(json.dumps(record) + "\n")
            
        logger.info(f"Audit record {record_hash[:8]} committed to vault.")
        return record_hash

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify the entire audit chain.
        Ensures no records have been modified, deleted, or inserted.
        """
        if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
            return {"status": "EMPTY", "valid": True, "records_verified": 0}
            
        previous_hash = "GENESIS"
        records_verified = 0
        
        with open(self.storage_path, "r") as f:
            for i, line in enumerate(f, 1):
                try:
                    record = json.loads(line)
                    stored_hash = record["record_hash"]
                    
                    # 1. Check if record matches its own hash
                    record_to_hash = {k: v for k, v in record.items() if k != "record_hash"}
                    calculated_hash = hashlib.sha256(
                        json.dumps(record_to_hash, sort_keys=True).encode()
                    ).hexdigest()
                    
                    if stored_hash != calculated_hash:
                        return {
                            "valid": False,
                            "error": f"Record {i} hash mismatch",
                            "record_id": stored_hash,
                            "records_verified": records_verified
                        }
                    
                    # 2. Check if chain links correctly
                    if record["previous_hash"] != previous_hash:
                        return {
                            "valid": False,
                            "error": f"Record {i} chain link broken",
                            "record_id": stored_hash,
                            "records_verified": records_verified
                        }
                    
                    previous_hash = stored_hash
                    records_verified += 1
                    
                except Exception as e:
                    return {"valid": False, "error": f"Parsing error on record {i}: {str(e)}"}
                    
        return {
            "valid": True, 
            "status": "SECURE", 
            "records_verified": records_verified,
            "last_hash": previous_hash
        }

    def get_records(self, limit: int = 50) -> List[Dict]:
        """Retrieve recent audit records."""
        records = []
        if not self.storage_path.exists():
            return []
            
        with open(self.storage_path, "r") as f:
            # Simple read from end could be optimized, but for prototype:
            lines = f.readlines()
            for line in lines[-limit:]:
                records.append(json.loads(line))
        
        return list(reversed(records))

if __name__ == "__main__":
    # Test Vault
    vault = AuditVault("./data/test_audit.jsonl")
    
    # Clean test file
    if vault.storage_path.exists():
        vault.storage_path.unlink()
    vault.storage_path.touch()
    
    print("--- Logging First Event ---")
    vault.log_event(
        advisor_id="EMP-001",
        query="What is the Smith relationship?",
        reasoning_trace=[{"step": 1, "thought": "Analyzing..."}],
        response="Total value is $3.3M"
    )
    
    print("--- Logging Second Event ---")
    vault.log_event(
        advisor_id="EMP-001",
        query="Is Smith eligible for SBA?",
        reasoning_trace=[{"step": 1, "thought": "Checking DSCR..."}],
        response="Yes, DSCR is 1.35."
    )
    
    print("\n--- Verifying Integrity ---")
    verification = vault.verify_integrity()
    print(f"Status: {verification['status']}, Valid: {verification['valid']}, Records: {verification['records_verified']}")
    
    # Test Tampering
    print("\n--- Simulating Tampering ---")
    with open(vault.storage_path, "r") as f:
        lines = f.readlines()
    
    # Modify second record
    record = json.loads(lines[1])
    record["response"] = "TAMPERED: Total value is $0"
    lines[1] = json.dumps(record) + "\n"
    
    with open(vault.storage_path, "w") as f:
        f.writelines(lines)
        
    verification = vault.verify_integrity()
    print(f"Integrity after tampering: {verification['valid']} - Error: {verification.get('error')}")
