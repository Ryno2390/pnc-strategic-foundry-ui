<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# PNC Strategic Foundry

A customer-centered AI platform that transforms siloed banking data into unified relationship intelligence. The Strategic Foundry serves as the R&D hub for the **PNC Strategic Advisor**, a reasoning-capable assistant for banking professionals.

## 🏗️ Architecture: The Three Pillars

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PNC STRATEGIC FOUNDRY                               │
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │   BRAIN     │     │   BRIDGE    │     │   MEMORY    │                   │
│  │ S1 Reasoning│────▶│  Context    │────▶│ Relationship│                   │
│  │   Model     │     │  Assembler  │     │    Store    │                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

1.  **The Brain (S1 Model):** Fine-tuned reasoning models (Qwen 2.5 3B / Llama 3.1 8B) trained to follow the "Brilliantly Boring" professional philosophy.
2.  **The Bridge (Context Assembler):** A tool-use layer that translates natural language queries into structured data lookups.
3.  **The Memory (Relationship Store):** A unified entity graph created via multi-weighted identity resolution across Consumer, Commercial, and Wealth Management LOBs.

---

## 🚀 Key Components



### 1. PNC Strategic Advisor (macOS App)

A native SwiftUI application designed for banking advisors.

- **100% Local Inference:** Runs on Apple Silicon using MLX.

- **Privacy First:** Data never leaves the device.

- **Quantization Pipeline:** `quantize_model.py` automates model optimization for edge delivery.



### 2. Knowledge Pillar: Policy RAG

Enables the AI to reason over internal bank regulations.

- **Contextual Intelligence:** Indexes markdown/PDF policies (SBA, Mortgage) for semantic retrieval.

- **Searchable Rules:** `policy_engine.py` allows advisors to query bank policy using natural language.



### 3. Visual Relationship Explorer

An interactive graph visualization of the Unified Entity Graph.

- **Network Insights:** Built with `react-force-graph`, allowing advisors to visually traverse connections between personal and commercial relationships.

- **Location:** `src/frontend/components/RelationshipGraph.tsx`



### 4. Deterministic Financial Guardrails

Hard-coded logic layer to verify AI-generated financial advice.

- **Compliance Enforcement:** Calculates DTI and DSCR metrics to validate product recommendations.

- **Safety First:** Adheres to the "Responsible Since 1865" philosophy by cross-checking reasoning traces.



---



## 🛠️ Getting Started



### Backend & CLI Tools

**Prerequisites:** Python 3.11+, Apple Silicon (highly recommended)



1.  **Initialize Environment:**

    ```bash

    python -m venv .venv

    source .venv/bin/activate

    pip install -r requirements.txt

    ```



2.  **Start the API Server:**

    ```bash

    python src/backend/app.py

    ```



3.  **Access Documentation:** Open `http://localhost:8000/docs` for the Interactive Swagger UI.



---



## 📂 Project Structure



```

├── src/

│   ├── backend/               # Core Python logic

│   │   ├── relationship_engine/ # Identity resolution, Tool-use, & Guardrails

│   │   ├── policy_engine.py   # Policy RAG Indexer & Search

│   │   ├── quantize_model.py  # Model optimization script

│   │   └── app.py             # FastAPI Server Entry point

│   └── frontend/              # React/Vite source code

│       └── components/        # RelationshipGraph.tsx, ArtifactCard.tsx

├── data/                      # Unified data storage

│   ├── training/              # Training datasets & prompts

│   ├── relationship_store/    # Raw & resolved identity data

│   └── policies/              # Bank policy documents (Markdown/PDF)

├── assets/                    # Project assets (images, screenshots)

├── docs/                      # Documentation & instructions

└── outputs/                   # Fine-tuning outputs & quantized models

```

## 📜 Documentation
- [Golden Example](docs/GOLDEN_EXAMPLE.md) - Auditable reasoning trace for boardroom presentations.
- [Production Roadmap](docs/PRODUCTION_ROADMAP.md) - The Three Pillars framework for enterprise readiness.

## ⚖️ License
Proprietary - PNC Financial Services Group. All rights reserved.
