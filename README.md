<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />

# PNC Strategic Foundry
### *Transforming Siloed Data into Unified Relationship Intelligence*
</div>

---

## 🌟 Mission
The **PNC Strategic Foundry** is a customer-centered AI platform designed to move banking from reactive service to proactive strategic partnership. It serves as the R&D hub for the **PNC Strategic Advisor**, an enterprise-grade assistant that reasons over unified data while adhering strictly to the bank's "Brilliantly Boring" professional philosophy.

---

## 🏗️ 1. Architecture: The Three Pillars
The Foundry is built upon a modular "Three Pillars" framework that separates **Memory** (Data), **Bridge** (Integration), and **Brain** (Reasoning).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PNC STRATEGIC FOUNDRY Hub                           │
│                                                                             │
│      PILLAR 1: MEMORY           PILLAR 2: THE BRIDGE         PILLAR 3: BRAIN│
│    (Relationship Store)         (Context Assembler)        (Reasoning Model)│
│                                                                             │
│   ┌───────────────────┐        ┌───────────────────┐      ┌─────────────────┐│
│   │  CONSUMER CORE    │        │                   │      │   S1 REASONER   ││
│   ├───────────────────┤        │  Entitlement-     │      │ (Local MLX LM)  ││
│   │  COMMERCIAL CORE  │───────▶│  Aware Tool       │─────▶│                 ││
│   ├───────────────────┤        │  Orchestration    │      │  "Brilliantly   ││
│   │  WEALTH ADVISORY  │        │                   │      │    Boring"      ││
│   └─────────┬─────────┘        └─────────┬─────────┘      └────────┬────────┘│
│             │                            │                         │         │
│             ▼                            ▼                         ▼         │
│   ┌───────────────────┐        ┌───────────────────┐      ┌─────────────────┐│
│   │ Unified Entity    │        │  FastAPI REST     │      │ AI Self-        ││
│   │ Graph (Identity   │        │  Gateway          │      │ Improving       ││
│   │ Resolution)       │        │                   │      │ Flywheel        ││
│   └───────────────────┘        └───────────────────┘      └─────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 2. Pillar 1: The Memory (Data Layer)
At the core of the Foundry is the **Unified Entity Graph**, which resolves identities across disparate lines of business (LOBs).

### Scalable Identity Resolution
Unlike standard $O(n^2)$ matchers, the Foundry uses a **Scalable Blocking Strategy** to handle enterprise datasets.
- **Inverted Indexing**: Entities are indexed by `Zip Code` and `Last Name Prefix`.
- **Performance**: Reduced comparisons by **16x** on initial benchmarks.
- **Weighted Scoring**:
  | Factor | Weight | Importance |
  | :--- | :--- | :--- |
  | SSN Last 4 | 40% | Primary Anchor |
  | Date of Birth | 20% | Critical Differentiator |
  | Name Similarity | 15% | Fuzzy Logic (John vs. Jonathan) |
  | Address Match | 15% | Physical Verification |
  | Contact (Ph/Email)| 10% | Auxiliary Signal |

---

## 🌉 3. Pillar 2: The Bridge (Integration Layer)
The Bridge translates the AI's reasoning into concrete actions through the **Context Assembler**.

### Entitlement-Aware Data Access
Advisors only see what they are licensed to see.
- **Retail Banker**: Accesses `CONSUMER_CORE` only.
- **Wealth Advisor**: Accesses `WEALTH_ADVISORY` + relevant `CONSUMER` links.
- **Relationship Manager**: Full cross-LOB 360-degree view.

### API Gateway (`app.py`)
A modern **FastAPI** hub that exposes the Foundry's intelligence via REST:
- `GET /api/v1/customer/{id}`: Unified 360-degree profile.
- `GET /api/v1/graph/data`: JSON nodes/edges for visualization.
- `GET /api/v1/policy/search`: Natural language query of bank rules.

---

## 🧠 4. Pillar 3: The Brain (AI Reasoning)
The Foundry uses specialized **S1 Reasoning Models** (Qwen 2.5 3B / Llama 3.1 8B) fine-tuned for high-fidelity financial analysis.

### The AI Flywheel
A self-correcting loop that ensures the model improves every single day.
1. **TRAIN**: Fine-tune Student (S1) on gold-standard traces.
2. **GENERATE**: S1 creates new reasoning traces for complex queries.
3. **GRADE**: Teacher (Claude 3.5 Sonnet) scores traces for accuracy and tone.
4. **MERGE**: High-quality traces (Score 8+) are folded back into the training set.

### Model Forge (Quantization)
To run **100% locally on an Advisor's Mac**, we automate the optimization pipeline:
- **MLX Conversion**: Fused weights converted to 4-bit and 8-bit.
- **Edge Performance**: ~55 tokens/second on M-series chips with <2GB RAM.

---

## 🛡️ 5. The Compliance Pillar (Reg-Tech)
We operationalize banking regulations directly into the source code to ensure safety.

| Regulation | Component | Functional Impact |
| :--- | :--- | :--- |
| **Reg B (ECOA)** | Adverse Action Reasoner | Generates formal denial notices citing specific math (DSCR/DTI). |
| **GLBA** | Privacy Scorer | Calculates **K-Anonymity** to prevent re-identification. |
| **Fair Lending** | Fairness Monitor | Real-time redaction of prohibited factors (Race, Gender, Zip Code). |
| **SEC 17a-4** | Immutable Audit Vault | Cryptographic hash chain proving AI reasoning hasn't been tampered with. |

### Immutable Audit Vault Schematic
```text
[ Advisor Query ] ─▶ [ S1 Reasoner ] ─▶ [ Final Response ]
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Audit committed   │
                    │   to Vault (Hashed) │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐    ┌─────────────────────┐
                    │ Record N (Hash)     │───▶│ Record N+1 (Hash)   │
                    │ prev_hash: 0xA1B2   │    │ prev_hash: [Hash N] │
                    └─────────────────────┘    └─────────────────────┘
                         (Tamper-Evident Evidence Chain)
```

---

## 🔍 6. Visual Intelligence
The **Relationship Explorer** (`src/frontend/components/RelationshipGraph.tsx`) allows advisors to visually traverse the entity graph.
- **Node Colors**: Blue (Person), Amber (Business).
- **Edge Dynamics**: Real-time links between spouses, household members, and business owners.
- **Impact**: Makes "invisible" connections (e.g., a commercial client owning a secret wealth-managed entity) tangible.

---

## 🛠️ 7. Getting Started

### Backend & API Server
**Prerequisites:** Python 3.11+, Apple Silicon (M1/M2/M3/M4)

1. **Setup Environment**:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Initialize Memory**:
   ```bash
   python src/backend/synthetic_factory.py  # Generate R&D data
   python src/backend/relationship_engine/normalization_engine.py
   python src/backend/relationship_engine/identity_resolution.py
   ```
3. **Launch Gateway**:
   ```bash
   python src/backend/app.py
   ```

### Frontend & Dashboard
**Prerequisites:** Node.js

1. **Install & Launch**:
   ```bash
   npm install
   npm run dev
   ```
2. **Access**: Open `http://localhost:3000` for the Advisor Dashboard and `http://localhost:8000/docs` for the API documentation.

---

## 📂 8. Project Structure
```text
├── src/
│   ├── backend/               # Python Core Logic
│   │   ├── relationship_engine/ # Identity, Guardrails, Adverse Action
│   │   ├── audit_vault.py     # SEC-compliant cryptographic logging
│   │   ├── policy_engine.py   # RAG Engine for bank rules
│   │   ├── app.py             # FastAPI REST Hub
│   │   └── tests/             # Pytest logic verification suite
│   └── frontend/              # React/Vite Source
│       └── components/        # RelationshipGraph.tsx, ArtifactCard.tsx
├── data/                      # Structured Storage
│   ├── training/              # Flywheel prompts & reasoning traces
│   ├── relationship_store/    # Raw, Normalized, and Resolved records
│   └── policies/              # Markdown bank guidelines
├── assets/                    # Media & Visuals
├── docs/                      # Blueprints & Roadmaps
└── outputs/                   # Optimized MLX Model Weights
```

---

## ⚖️ License
**Proprietary - PNC Financial Services Group.** All rights reserved. "Responsible since 1865."