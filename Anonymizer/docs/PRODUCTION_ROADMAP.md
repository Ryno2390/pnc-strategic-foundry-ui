# PNC Strategic Foundry: Production Roadmap

## From Prototype to Boardroom

**Current State:** Working prototype on Apple M4 (16GB)
**Target State:** Bank-wide deployment serving thousands of advisors

---

## Three Pillars Framework

```
                    ┌─────────────────────────────────────┐
                    │      PRODUCTION-READY FOUNDRY       │
                    └─────────────────────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│                     │  │                     │  │                     │
│   PILLAR 1: TRUST   │  │  PILLAR 2: SCALE    │  │ PILLAR 3: KNOWLEDGE │
│   (Security)        │  │  (Hardware)         │  │ (RAG)               │
│                     │  │                     │  │                     │
│  • Encryption       │  │  • vLLM Hosting     │  │  • Policy Docs      │
│  • Access Control   │  │  • GPU Clusters     │  │  • Product Manuals  │
│  • Audit Logging    │  │  • Load Balancing   │  │  • Compliance Rules │
│                     │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## Pillar 1: The Trust Layer (Security)

### Why It Matters
Banks operate under strict regulatory requirements (OCC, FDIC, SEC). The AI system must demonstrate that customer data is protected and access is controlled.

### Implementation Checklist

#### 1.1 Encryption at Rest
```python
# Current: unified_entities.json stored in plaintext
# Target: AES-256 encrypted with key management

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecureRelationshipStore:
    """Encrypted storage for unified entities."""

    def __init__(self, master_key: bytes):
        self.cipher = Fernet(self._derive_key(master_key))

    def save_entities(self, entities: List[Dict], path: Path):
        """Save entities with encryption."""
        plaintext = json.dumps(entities).encode()
        ciphertext = self.cipher.encrypt(plaintext)
        path.write_bytes(ciphertext)

    def load_entities(self, path: Path) -> List[Dict]:
        """Load and decrypt entities."""
        ciphertext = path.read_bytes()
        plaintext = self.cipher.decrypt(ciphertext)
        return json.loads(plaintext)
```

**Key Management:**
- Integrate with PNC's existing HSM (Hardware Security Module)
- Rotate keys quarterly
- Separate keys per environment (Dev/UAT/Prod)

#### 1.2 Role-Based Access Control (RBAC)
```python
class AdvisorPermissions(Enum):
    """Permission levels for different advisor roles."""
    RETAIL_BANKER = "retail"           # Consumer data only
    BUSINESS_BANKER = "business"       # Commercial data only
    WEALTH_ADVISOR = "wealth"          # Wealth data only
    PRIVATE_BANKER = "private"         # All data (qualified)
    RELATIONSHIP_MANAGER = "rm"        # Full cross-LOB view

class AccessControlledAssembler(ContextAssembler):
    """Context Assembler with permission checks."""

    def __init__(self, advisor_id: str, permission_level: AdvisorPermissions):
        super().__init__()
        self.advisor_id = advisor_id
        self.permission = permission_level

    def get_customer_360(self, entity_id_or_name: str) -> Optional[Customer360]:
        """Get customer view filtered by advisor permissions."""
        full_view = super().get_customer_360(entity_id_or_name)

        if not full_view:
            return None

        # Filter based on permission level
        if self.permission == AdvisorPermissions.RETAIL_BANKER:
            full_view.wealth_portfolios = []  # Redact wealth data
            full_view.business_connections = []  # Redact business data

        elif self.permission == AdvisorPermissions.WEALTH_ADVISOR:
            full_view.personal_accounts = []  # Only show wealth portfolios

        # Log access for audit trail
        self._log_access(entity_id_or_name, self.advisor_id)

        return full_view
```

**Permission Matrix:**

| Role | Consumer | Commercial | Wealth | Cross-LOB Insights |
|------|----------|------------|--------|-------------------|
| Retail Banker | FULL | NONE | NONE | NONE |
| Business Banker | NONE | FULL | NONE | NONE |
| Wealth Advisor | LIMITED | NONE | FULL | NONE |
| Private Banker | FULL | FULL | FULL | FULL |
| Relationship Manager | FULL | FULL | FULL | FULL |

#### 1.3 Immutable Audit Logging

**Why Immutability is Non-Negotiable:**

In banking, regulators (OCC, FDIC, SEC, FINRA) require proof that neither advisors nor AI systems altered their reasoning after the fact. This is critical for:
- **Suitability disputes** - "Why did you recommend this product?"
- **Fair lending audits** - "Did the AI apply consistent criteria?"
- **Fraud investigations** - "What data did the advisor access?"

The audit log must be:
1. **Immutable** - Records cannot be modified once written
2. **Append-only** - New records can only be added, never deleted
3. **Cryptographically verifiable** - Hash chains prove integrity
4. **Tamper-evident** - Any modification attempt is detectable

```python
import hashlib
from datetime import datetime
from typing import List, Dict, Any
import json

class ImmutableAuditLogger:
    """
    Append-only, cryptographically-verified audit log.

    Each record includes a hash of the previous record, creating
    an unbreakable chain. Any tampering breaks the chain and is
    immediately detectable.

    Regulatory Compliance:
    - SEC Rule 17a-4: Electronic records must be non-rewriteable
    - FINRA Rule 4511: Books and records preservation
    - OCC Guidelines: AI model decision documentation
    """

    def __init__(self, storage_backend):
        self.storage = storage_backend  # WORM storage, blockchain, or immutable DB
        self.previous_hash = self._get_chain_head()

    def log_ai_reasoning(
        self,
        advisor_id: str,
        query: str,
        reasoning_trace: List[Dict],
        tool_calls: List[Dict],
        final_response: str,
        entities_accessed: List[str],
        data_sources_queried: List[str]
    ) -> str:
        """
        Log complete AI reasoning chain with cryptographic integrity.

        CRITICAL: This record becomes IMMUTABLE once written.
        Neither the advisor nor system administrators can modify it.
        """

        timestamp = datetime.utcnow()

        # Build the complete audit record
        audit_record = {
            # Temporal anchoring
            "record_id": self._generate_record_id(),
            "timestamp_utc": timestamp.isoformat() + "Z",
            "timestamp_unix": int(timestamp.timestamp() * 1000),

            # Actor identification
            "advisor_id": advisor_id,
            "advisor_role": self._get_advisor_role(advisor_id),
            "session_id": self._get_session_id(),
            "client_ip": self._get_client_ip(),
            "workstation_id": self._get_workstation_id(),

            # The complete reasoning chain (PRESERVED EXACTLY)
            "query_original": query,
            "query_hash": hashlib.sha256(query.encode()).hexdigest(),
            "reasoning_trace": reasoning_trace,  # Every step S1 took
            "tool_calls": tool_calls,            # Every tool invocation
            "final_response": final_response,    # What the advisor saw
            "response_hash": hashlib.sha256(final_response.encode()).hexdigest(),

            # Data access footprint
            "entities_accessed": entities_accessed,
            "data_sources": data_sources_queried,
            "permission_level_at_access": self._get_permission(advisor_id),

            # Cryptographic chain integrity
            "previous_record_hash": self.previous_hash,
            "record_hash": None  # Computed below
        }

        # Compute hash of this record (excluding the hash field itself)
        record_for_hashing = {k: v for k, v in audit_record.items() if k != "record_hash"}
        record_hash = hashlib.sha256(
            json.dumps(record_for_hashing, sort_keys=True).encode()
        ).hexdigest()
        audit_record["record_hash"] = record_hash

        # Write to IMMUTABLE storage (append-only)
        self._write_immutable(audit_record)

        # Update chain head
        self.previous_hash = record_hash

        return record_hash

    def verify_chain_integrity(self, start_record: str = None) -> Dict[str, Any]:
        """
        Verify the entire audit chain has not been tampered with.

        Run this daily (or on-demand for investigations) to prove
        no records have been modified, deleted, or inserted.
        """
        records = self.storage.read_all(start_from=start_record)

        previous_hash = start_record or "GENESIS"
        broken_at = None
        records_verified = 0

        for record in records:
            # Recompute what the hash SHOULD be
            record_for_hashing = {k: v for k, v in record.items() if k != "record_hash"}
            expected_hash = hashlib.sha256(
                json.dumps(record_for_hashing, sort_keys=True).encode()
            ).hexdigest()

            # Check 1: Record hash matches content
            if record["record_hash"] != expected_hash:
                broken_at = record["record_id"]
                break

            # Check 2: Chain links correctly
            if record["previous_record_hash"] != previous_hash:
                broken_at = record["record_id"]
                break

            previous_hash = record["record_hash"]
            records_verified += 1

        return {
            "chain_valid": broken_at is None,
            "records_verified": records_verified,
            "broken_at_record": broken_at,
            "verification_timestamp": datetime.utcnow().isoformat()
        }

    def _write_immutable(self, record: Dict):
        """
        Write to append-only storage.

        Options for production:
        1. AWS S3 with Object Lock (WORM compliance)
        2. Azure Immutable Blob Storage
        3. Dedicated blockchain/DLT
        4. PostgreSQL with row-level security + triggers preventing UPDATE/DELETE
        5. Splunk with locked indexes
        """
        self.storage.append(record)  # APPEND ONLY - no update/delete methods exist
```

**Storage Architecture for Immutability:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMMUTABLE AUDIT STORAGE                              │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Record 1   │───▶│  Record 2   │───▶│  Record 3   │───▶│  Record N   │  │
│  │             │    │             │    │             │    │             │  │
│  │ hash: a1b2  │    │ prev: a1b2  │    │ prev: c3d4  │    │ prev: ...   │  │
│  │             │    │ hash: c3d4  │    │ hash: e5f6  │    │ hash: ...   │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│        │                  │                  │                  │          │
│        ▼                  ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    WORM STORAGE LAYER                               │   │
│  │          (Write Once, Read Many - Cannot Delete/Modify)             │   │
│  │                                                                     │   │
│  │  Options:                                                           │   │
│  │  • AWS S3 Object Lock (Governance or Compliance mode)               │   │
│  │  • Azure Immutable Blob Storage                                     │   │
│  │  • NetApp ONTAP with SnapLock                                       │   │
│  │  • Dedicated audit appliance (e.g., Veritas)                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**What Gets Preserved Forever:**

| Field | Purpose | Regulatory Requirement |
|-------|---------|----------------------|
| `reasoning_trace` | Complete AI thought process | OCC AI Guidance - Explainability |
| `tool_calls` | Every data lookup | SEC 17a-4 - Complete records |
| `entities_accessed` | Which customers viewed | GLBA - Privacy audit |
| `advisor_id` + `timestamp` | Who, when | FINRA 4511 - Books & records |
| `query_hash` + `response_hash` | Integrity proof | SOX 802 - Record integrity |
| `previous_record_hash` | Chain continuity | Tamper evidence |

**Example Audit Record (What Regulators See):**

```json
{
  "record_id": "AUD-2025-12-23-00847293",
  "timestamp_utc": "2025-12-23T15:42:18.293Z",
  "advisor_id": "EMP-78234",
  "advisor_role": "PRIVATE_BANKER",

  "query_original": "What is the total relationship value for the Smith household?",
  "query_hash": "8f14e45f...",

  "reasoning_trace": [
    {"step": 1, "thought": "Parsing query for household aggregation..."},
    {"step": 2, "thought": "Identified 'Smith' as target household..."},
    {"step": 3, "thought": "Selecting get_household_summary tool..."},
    {"step": 4, "tool_call": "get_household_summary('Smith')", "result_summary": "3 members, $3.32M"},
    {"step": 5, "thought": "Synthesizing response with cross-LOB insight..."}
  ],

  "final_response": "The Smith household has a total relationship value of $3,320,100.66...",
  "response_hash": "7d793037...",

  "entities_accessed": ["UNI-0002", "UNI-0003", "UNI-0012", "BIZ-001"],
  "data_sources": ["CONSUMER_CORE", "WEALTH_ADVISORY", "COMMERCIAL_CORE"],

  "previous_record_hash": "3b4c5d6e7f...",
  "record_hash": "9a8b7c6d5e..."
}
```

**Compliance Certification:**
This audit architecture meets requirements for:
- SEC Rule 17a-4(f) - Electronic storage media
- FINRA Rule 4511 - Books and records
- OCC 2021-27 - Model risk management for AI
- GLBA Safeguards Rule - Access logging
- SOX Section 802 - Document integrity

---

## Pillar 2: The Scale Layer (Hardware)

### Why It Matters
The M4 prototype handles single-user queries. Production needs to serve 5,000+ advisors with sub-second response times.

### Architecture Evolution

```
PROTOTYPE (Current)                    PRODUCTION (Target)
─────────────────────                  ─────────────────────

┌─────────────────┐                    ┌─────────────────────────────────┐
│    M4 Mac       │                    │       LOAD BALANCER             │
│    (16GB)       │                    │      (F5 / AWS ALB)             │
│                 │                    └───────────┬─────────────────────┘
│  MLX-LM Local   │                                │
│  Single User    │                    ┌───────────┼───────────┐
└─────────────────┘                    │           │           │
                                       ▼           ▼           ▼
                              ┌─────────────┬─────────────┬─────────────┐
                              │   vLLM      │   vLLM      │   vLLM      │
                              │  Server 1   │  Server 2   │  Server 3   │
                              │  (8xA100)   │  (8xA100)   │  (8xA100)   │
                              └─────────────┴─────────────┴─────────────┘
                                       │           │           │
                                       └───────────┼───────────┘
                                                   │
                                       ┌───────────▼───────────┐
                                       │   RELATIONSHIP STORE   │
                                       │   (PostgreSQL + Redis) │
                                       └───────────────────────┘
```

### Implementation Checklist

#### 2.1 Model Serving with vLLM
```bash
# Convert LoRA adapter to merged model
python -m mlx_lm.merge \
    --base-model Qwen/Qwen2.5-3B-Instruct \
    --adapter-path ./adapters/s1_banking_v3 \
    --output-path ./models/s1_banking_merged

# Convert to Hugging Face format for vLLM
python scripts/convert_mlx_to_hf.py \
    --input ./models/s1_banking_merged \
    --output ./models/s1_banking_hf

# Deploy with vLLM (on GPU server)
python -m vllm.entrypoints.openai.api_server \
    --model ./models/s1_banking_hf \
    --tensor-parallel-size 8 \
    --max-num-seqs 256 \
    --gpu-memory-utilization 0.9
```

#### 2.2 Infrastructure Requirements

| Component | Specification | Quantity | Purpose |
|-----------|--------------|----------|---------|
| GPU Nodes | 8x NVIDIA A100 (80GB) | 3 | Model inference |
| CPU Nodes | 64-core AMD EPYC | 6 | Context assembly, preprocessing |
| Memory | 512GB RAM per node | 9 | Fast data access |
| Storage | NVMe SSD (10TB) | RAID array | Relationship store |
| Network | 100Gbps InfiniBand | Mesh | Low-latency communication |

#### 2.3 Performance Targets

| Metric | Prototype | Production Target |
|--------|-----------|-------------------|
| Concurrent Users | 1 | 5,000+ |
| Query Latency (p50) | 2-3s | <500ms |
| Query Latency (p99) | 5s | <2s |
| Throughput | 10 queries/min | 10,000 queries/min |
| Availability | N/A | 99.9% |

#### 2.4 Caching Strategy
```python
class CachedContextAssembler(ContextAssembler):
    """Context Assembler with Redis caching."""

    def __init__(self, redis_client):
        super().__init__()
        self.cache = redis_client
        self.cache_ttl = 300  # 5 minutes

    def get_household_summary(self, household_name: str) -> Dict:
        """Get household summary with caching."""
        cache_key = f"household:{household_name.upper()}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            return json.loads(cached)

        # Cache miss - compute and store
        result = super().get_household_summary(household_name)
        self.cache.setex(cache_key, self.cache_ttl, json.dumps(result))

        return result
```

---

## Pillar 3: The Knowledge Expansion (RAG)

### Why It Matters
S1 currently has "Customer Memory" (relationship data). Adding "Policy Memory" enables the AI to quote actual product terms, rates, and compliance requirements.

### Target Knowledge Sources

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        S1 KNOWLEDGE EXPANSION                               │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ CUSTOMER MEMORY │  │  POLICY MEMORY  │  │ PRODUCT MEMORY  │             │
│  │ (Current)       │  │  (Phase 1)      │  │  (Phase 2)      │             │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤             │
│  │ • Relationships │  │ • Mortgage Regs │  │ • Current Rates │             │
│  │ • Account Data  │  │ • SBA Guidelines│  │ • Fee Schedules │             │
│  │ • Holdings      │  │ • KYC/AML Rules │  │ • Product Terms │             │
│  │ • Transactions  │  │ • Privacy Laws  │  │ • Promotions    │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation: RAG Pipeline

```python
class PolicyRAG:
    """Retrieval-Augmented Generation for policy documents."""

    def __init__(self, vector_store, s1_model):
        self.vector_store = vector_store  # Pinecone, Weaviate, etc.
        self.s1_model = s1_model
        self.chunk_size = 512
        self.top_k = 5

    def ingest_document(self, pdf_path: Path, doc_type: str):
        """Ingest a policy PDF into the vector store."""
        # Extract text from PDF
        text = self._extract_pdf_text(pdf_path)

        # Chunk into overlapping segments
        chunks = self._chunk_text(text, self.chunk_size, overlap=50)

        # Generate embeddings and store
        for i, chunk in enumerate(chunks):
            embedding = self._generate_embedding(chunk)
            self.vector_store.upsert({
                "id": f"{pdf_path.stem}_{i}",
                "values": embedding,
                "metadata": {
                    "source": pdf_path.name,
                    "doc_type": doc_type,
                    "chunk_index": i,
                    "text": chunk
                }
            })

    def query_with_context(self, query: str, customer_context: Dict) -> str:
        """Answer query using both customer data and policy documents."""

        # Step 1: Retrieve relevant policy chunks
        query_embedding = self._generate_embedding(query)
        policy_chunks = self.vector_store.query(
            vector=query_embedding,
            top_k=self.top_k,
            include_metadata=True
        )

        # Step 2: Build augmented prompt
        prompt = f"""You are a PNC advisor assistant. Answer the question using:

CUSTOMER CONTEXT:
{json.dumps(customer_context, indent=2)}

RELEVANT POLICY INFORMATION:
{self._format_chunks(policy_chunks)}

QUESTION: {query}

Provide a helpful, accurate response citing specific policy sections where applicable."""

        # Step 3: Generate response with S1
        return self.s1_model.generate(prompt)
```

### Priority Document Types

| Priority | Document Type | Examples | Use Case |
|----------|--------------|----------|----------|
| P0 | Mortgage Guidelines | FHA/VA requirements, DTI limits | Loan qualification |
| P0 | SBA Loan Programs | 7(a), 504, Express requirements | Business lending |
| P1 | Fee Schedules | Account fees, wire fees, overdraft | Customer inquiries |
| P1 | Product Brochures | Credit card benefits, account features | Cross-sell |
| P2 | Compliance Manuals | BSA/AML, FCRA, TILA | Risk mitigation |
| P2 | Internal Procedures | Account opening, dispute resolution | Process questions |

### Enhanced Query Example

```
BEFORE (Customer Memory Only):
─────────────────────────────────────────────────────────────────────────────
Query: "Can the Smith family qualify for an SBA loan for their business?"

Response: "Smith Consulting LLC has annual revenue of $1.25M and
          total assets of $337,500. You should check SBA requirements."
─────────────────────────────────────────────────────────────────────────────

AFTER (Customer + Policy Memory):
─────────────────────────────────────────────────────────────────────────────
Query: "Can the Smith family qualify for an SBA loan for their business?"

Response: "Based on my analysis:

CUSTOMER DATA (Smith Consulting LLC):
• Annual Revenue: $1,250,000
• Years in Business: 5+ (since 2019)
• Ownership: John R. Smith (60%), Jane Smith (40%)
• Existing Debt: $125,000 LOC

SBA 7(a) ELIGIBILITY (per SBA SOP 50 10 7.1):
✅ For-profit business operating in the U.S.
✅ Meets size standards (under $8M for NAICS 541611)
✅ Owners have 20%+ stake (required for personal guarantee)
✅ Demonstrated ability to repay (current accounts in good standing)

RECOMMENDATION:
Smith Consulting LLC appears to qualify for an SBA 7(a) loan up to
$350,000 based on their financials. The current debt-to-income ratio
of 0.10 is well below the 0.43 maximum. Would you like me to prepare
a pre-qualification summary?"
─────────────────────────────────────────────────────────────────────────────
```

---

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-4)
- [ ] Implement encryption for relationship store
- [ ] Build RBAC framework
- [ ] Set up audit logging infrastructure
- [ ] Document security architecture for compliance review

### Phase 2: Scale Preparation (Weeks 5-8)
- [ ] Convert MLX model to vLLM-compatible format
- [ ] Provision GPU infrastructure (internal cloud or vendor)
- [ ] Implement caching layer
- [ ] Load test with synthetic advisor traffic

### Phase 3: Knowledge Expansion (Weeks 9-12)
- [ ] Build RAG pipeline infrastructure
- [ ] Ingest priority P0 documents (Mortgage, SBA)
- [ ] Test policy-augmented responses
- [ ] Validate accuracy with subject matter experts

### Phase 4: Pilot (Weeks 13-16)
- [ ] Deploy to limited advisor group (50 users)
- [ ] Gather feedback and iterate
- [ ] Monitor performance and accuracy metrics
- [ ] Prepare for broader rollout

---

## Success Metrics

| Pillar | Metric | Target |
|--------|--------|--------|
| **Trust** | Zero data breaches | 0 incidents |
| **Trust** | Audit compliance rate | 100% |
| **Scale** | Query latency (p99) | <2 seconds |
| **Scale** | System availability | 99.9% |
| **Knowledge** | Policy citation accuracy | >95% |
| **Knowledge** | Advisor satisfaction | >4.5/5.0 |

---

## Appendix: Cost Estimation

### Infrastructure (Annual)

| Component | Unit Cost | Quantity | Annual Cost |
|-----------|----------|----------|-------------|
| GPU Nodes (A100 8x) | $50,000/mo | 3 | $1,800,000 |
| CPU Nodes | $5,000/mo | 6 | $360,000 |
| Storage (NVMe) | $2,000/mo | 10TB | $24,000 |
| Vector DB (Pinecone) | $1,000/mo | Enterprise | $12,000 |
| Monitoring (Datadog) | $500/mo | - | $6,000 |
| **Total Infrastructure** | | | **$2,202,000** |

### Personnel (Annual)

| Role | Count | Salary | Total |
|------|-------|--------|-------|
| ML Engineers | 3 | $200,000 | $600,000 |
| Platform Engineers | 2 | $180,000 | $360,000 |
| Security Engineer | 1 | $190,000 | $190,000 |
| Product Manager | 1 | $170,000 | $170,000 |
| **Total Personnel** | 7 | | **$1,320,000** |

### Total Year 1 Investment: ~$3.5M

### ROI Projection
- Advisor time savings: 15 min/day x 5,000 advisors = 1,250 hours/day
- At $50/hour fully loaded cost = $62,500/day in productivity
- Annual productivity gain: **$15.6M**
- **ROI: 4.5x in Year 1**

---

**Document Version:** 1.0
**Last Updated:** December 23, 2025
**Author:** PNC Strategic Foundry Team
