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
- **Location:** `PNCAdvisor/`
- **Setup:** Open `PNCAdvisor/Package.swift` in Xcode 15+.

### 2. Defense-in-Depth PII Anonymizer
A multi-layered orchestrator for ensuring data privacy in LLM traces.
- **Layer 1 (Regex):** Deterministic scrubbing of SSNs, accounts, and emails.
- **Layer 2 (NER):** Structural detection using Microsoft Presidio (SpaCy).
- **Layer 3 (Cognitive):** Context-aware scrubbing using a fine-tuned 3B model to catch "unique fingerprint" identifiers.
- **Location:** `orchestrator.py`

### 3. The AI Flywheel
A self-improving training loop that leverages "Teacher" models to upgrade "Student" models.
- **Loop:** Train → Generate → Grade (Claude 3.5) → Merge → Repeat.
- **Features:** Teacher injection for cold-starts and "Near-Miss" analysis for error correction.
- **Location:** `flywheel.py`

---

## 🛠️ Getting Started

### Backend & CLI Tools
**Prerequisites:** Python 3.11+, Apple Silicon (highly recommended)

1.  **Initialize Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt # or install manually: mlx-lm anthropic presidio-analyzer spacy
    python -m spacy download en_core_web_lg
    ```

2.  **Run the Relationship Engine Demo:**
    ```bash
    python relationship_engine/s1_advisor_demo.py
    ```

3.  **Start the Flywheel Status Center:**
    ```bash
    python flywheel.py status
    ```

### Web Frontend
**Prerequisites:** Node.js

1.  **Install & Run:**
    ```bash
    npm install
    npm run dev
    ```
2.  **Environment:** Set `GEMINI_API_KEY` in `.env.local` for the web-based reasoning demo.

---

## 📂 Project Structure



```

├── src/

│   ├── backend/               # Core Python logic (Flywheel, Anonymizer)

│   │   ├── relationship_engine/ # Identity resolution & Tool-use

│   │   ├── fine_tuning/       # Training scripts

│   │   └── s1_adapter/        # Trained model weights

│   └── frontend/              # React/Vite source code

├── data/                      # Unified data storage

│   ├── training/              # Training datasets & prompts

│   └── relationship_store/    # Raw & resolved identity data

├── assets/                    # Project assets (images, screenshots)

├── docs/                      # Documentation & instructions

├── PNCAdvisor/                # Native macOS SwiftUI Application

└── outputs/                   # Fine-tuning outputs & quantized models

```

## 📜 Documentation
- [Golden Example](docs/GOLDEN_EXAMPLE.md) - Auditable reasoning trace for boardroom presentations.
- [Production Roadmap](docs/PRODUCTION_ROADMAP.md) - The Three Pillars framework for enterprise readiness.

## ⚖️ License
Proprietary - PNC Financial Services Group. All rights reserved.
