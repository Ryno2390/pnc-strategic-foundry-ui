<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# PNC Strategic Foundry

A customer-centered AI platform that transforms siloed banking data into unified relationship intelligence.

## Architecture Overview

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

## Components

### Frontend (UI)
**Prerequisites:** Node.js

1. Install dependencies: `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local)
3. Run the app: `npm run dev`

### Backend (AI Engine)
**Prerequisites:** Python 3.11+, Apple Silicon (for MLX)

1. Create virtual environment: `python -m venv .venv && source .venv/bin/activate`
2. Install dependencies: `pip install mlx-lm anthropic`
3. Run the relationship engine demo:
   ```bash
   python relationship_engine/s1_advisor_demo.py
   ```

## Key Features

### Identity Resolution Engine
- Weighted scoring algorithm (SSN 40%, DOB 20%, Name 15%, Address 15%)
- Confidence thresholds: Auto-merge (≥0.95), Human-in-loop (0.70-0.94), Keep separate (<0.70)
- Cross-LOB normalization (Consumer, Commercial, Wealth Management)

### AI Flywheel
- Teacher (Claude) → Student (S1) → Grading → Retraining cycle
- Teacher injection for cold-start problem
- MLX-LM fine-tuning on Apple Silicon

### Tool-Use Functions
- `get_customer_360(name)` - Complete customer relationship view
- `get_household_summary(last_name)` - Aggregated household financials
- `search_entities(query)` - Entity search

## Documentation

- [Golden Example](docs/GOLDEN_EXAMPLE.md) - Auditable reasoning trace for boardroom presentations
- [Production Roadmap](docs/PRODUCTION_ROADMAP.md) - Three Pillars framework (Trust/Scale/Knowledge)

## Project Structure

```
├── docs/                      # Documentation
│   ├── GOLDEN_EXAMPLE.md      # End-to-end demo trace
│   └── PRODUCTION_ROADMAP.md  # Production readiness guide
├── relationship_engine/       # Customer 360 backend
│   ├── context_assembler.py   # Tool-use functions (the Bridge)
│   ├── identity_resolution.py # Weighted matching algorithm
│   ├── normalization_engine.py# Data standardization
│   └── s1_advisor_demo.py     # End-to-end demo
├── flywheel.py               # AI training orchestrator
├── generate_traces.py        # S1 trace generation
├── grade_with_claude.py      # Teacher grading system
└── teacher_injection.py      # Gold-standard example generation
```

## License

Proprietary - PNC Financial Services Group
