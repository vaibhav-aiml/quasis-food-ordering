# Intent-to-Action Shopping Agent

An agentic system that turns a natural-language shopping intent ("making biryani,
need onions and curd, cheapest option under 20 min") into a completed order on a
native Android quick-commerce app (Zepto, Blinkit, Instamart) — via LLM reasoning
for understanding, deterministic Python for ranking/decisions, and Appium for UI
automation.

See [`docs/phase0_architecture.md`](docs/phase0_architecture.md) for the full
architecture, and [`docs/phase1_project_plan.md`](docs/phase1_project_plan.md)
for the development workflow and setup steps below.

## Status

Project is being built phase-by-phase. Currently at **Phase 1 — Project Setup**.
No application code exists yet; this phase only establishes the environment and
folder skeleton.

## Quickstart (local dev)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
```

There is nothing to run yet — `main.py` and the FastAPI app arrive in Phase 2.
This quickstart exists so the environment can be verified now (see
`docs/phase1_project_plan.md` → Manual Verification).

## Repository layout

```
shopping-agent/
├── backend/     # Python/FastAPI/LangGraph application (see docs for structure)
├── mobile/      # Flutter client (scaffolded in a later phase)
└── docs/        # Architecture and per-phase design documents
```
