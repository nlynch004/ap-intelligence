# AP Intelligence

**The living memory of AP's partnership decisions, relationships, and outcomes.**

A prototype of a governed institutional-memory layer for Acceleration Partners account teams. It
turns normal account-team conversation into structured, versioned memory claims; detects and
resolves contradictions without deleting history; and combines current client memory with
privacy-safe cross-client portfolio experience to make (and remember) a real renewal decision.

Full product spec: [`../PROJECT_AP_Intelligence_Graph.md`](../PROJECT_AP_Intelligence_Graph.md).

## Quick start

Two servers, run in separate terminals.

### Backend

```bash
cd backend
uv venv                     # first time only
uv pip install -e ".[dev]"  # first time only - or see note below
cp .env.example .env        # add OPENAI_API_KEY here if/when you have one
uv run uvicorn app.main:app --reload --port 8000
```

> Note: this repo installs dependencies directly (`uv pip install fastapi ...`) rather than as an
> editable package, because `backend/` has both `app/` and `data/` at its root (see
> `pyproject.toml`'s `[tool.uv] package = false`). `uv pip install -e ".[dev]"` will fail with a
> "multiple top-level packages" error - just run:
> `uv pip install "fastapi>=0.115" "uvicorn[standard]>=0.30" "pydantic>=2.7" "sqlalchemy>=2.0" "python-dotenv>=1.0" "openai>=1.40" "httpx>=0.27" "pytest>=8.0"`

The database is SQLite (`backend/data/app.db`) and is auto-seeded on first startup from
`backend/data/northwind_seed.json` (real case-study data) and `backend/data/synthetic_portfolio.json`
(fictional cross-client portfolio, regenerate with `uv run python data/generate_synthetic_portfolio.py`).
To force a clean reseed: `rm backend/data/app.db` and restart, or `uv run python -m app.seed --reset`.

Run tests: `uv run pytest tests/ -q`

### Frontend

```bash
cd frontend
npm install   # first time only
npm run dev
```

Open **http://localhost:3000**. It talks to the backend at `http://localhost:8000`
(`frontend/.env.local`, `NEXT_PUBLIC_API_URL`).

## The demo script (spec Sec.19)

Type each of these into the chat panel, in order:

1. **`Bring me up to speed on Northwind's partnership with Summit Sisters.`** — retrieves active
   memory only. At this point the old `aggressively grow coupon partnerships` strategy is still
   active. (The query itself is a broad, unscoped pull of every active claim for this client, not
   partner-filtered - it's just that Summit Sisters is still the only partner with governed
   relationship memory at a fresh reset, so naming her keeps the prompt honest about what the
   answer will cover.)
2. **`Northwind's strategy changed after last week's executive review. They now want to reduce
   coupon dependence and prioritize new-customer growth, even if short-term ROAS is a little
   lower.`** — the extraction agent proposes 3 candidate memories. Approve them (individually or
   "Approve all"). The strategy candidate conflicts with the old belief - a conflict dialog opens.
   Choose **Supersede**. The old strategy node goes dim/dashed in the graph but stays visible.
3. **`Bring me up to speed on Northwind's partnership with Summit Sisters.`** again — the old
   strategy no longer appears; the new one does. This is the "changes its mind without forgetting
   its history" moment.
4. **`Summit Sisters wants $6,000 for another campaign. Should we renew them?`** — a structured
   recommendation appears (renegotiate & test, $3,500 base + 10% performance bonus), citing the
   attribution hypothesis as an explicit uncertainty and the synthetic portfolio pattern as
   supporting evidence. The cited memory/pattern nodes highlight in the graph.
5. Click **Accept recommendation** — creates a Decision node with edges back to every claim that
   motivated it.
6. Click **Simulate future outcome** (explicitly demo-only) — creates an Outcome node and bumps the
   portfolio pattern's evidence count **31 → 32**.

Click any node in the graph at any point to inspect its full memory metadata (status, confidence,
authority, source, supersession chain) in the right panel.

## What's real vs stubbed (spec Sec.30)

**Real:** natural-language memory extraction, schema validation, candidate review, deterministic
conflict detection, supersession, graph update, active-memory retrieval, evidence-aware
recommendation generation (with a genuine deterministic fallback - see below, not a toy stub),
decision capture, outcome insertion, portfolio evidence-count update, source-authority weighting,
cross-client privacy scoping (client-private vs. privacy-safe portfolio claims).

**Stubbed / simplified:** no auth/SSO/RBAC, no real APVision integration, no real cross-client
portfolio data (clearly labeled synthetic), no vector/semantic search (deterministic keyword +
entity + authority + recency scoring instead - spec explicitly allows this for the prototype), no
background pattern-discovery job (the one portfolio pattern is pre-seeded and approved), `simulate
future outcome` fabricates a plausible result rather than waiting on a real campaign cycle, and it
runs as one FastAPI process rather than on AgentCore/Bedrock.

## LLM provider

`app/llm/factory.py` picks `OpenAIProvider` if `OPENAI_API_KEY` is set in `backend/.env`, otherwise
`MockProvider` - a deterministic, rule-based provider tuned to the exact demo script above, not a
no-op stub. Every acceptance-criteria item runs correctly with zero API key. Adding a key upgrades
extraction/recommendation quality and generality with no code changes; a failed live call at
request time (bad key, rate limit, network) falls back to the mock automatically
(`llm/factory.py::call_with_fallback`) so a mid-demo API hiccup never breaks the flow.

## Data provenance

- `backend/data/northwind_seed.json` - transcribed directly from the supplied
  `Case Study Data Pack - Director of Applied AI_July 2026.xlsx`. The attribution hypothesis
  (promo-code leakage on the 2026-05 Summit Sisters campaign: 1,847 redemptions vs 385 clicks) is
  **derived deterministically** at seed time from those numbers (`app/seed.py::_derive_attribution_hypothesis`),
  not hardcoded.
- `backend/data/synthetic_portfolio.json` - fully fictional, generated by
  `data/generate_synthetic_portfolio.py` (fixed random seed for reproducibility). Every synthetic
  record is tagged `synthetic: true` and surfaced as such in the graph and inspector.

## Architecture at a glance

```
frontend/  Next.js + TypeScript + React Flow (@xyflow/react) + Tailwind
backend/
  app/main.py           FastAPI app, CORS, startup seed
  app/models.py          clients, partners, campaigns, team_members, memory_claims,
                          memory_edges, decisions, outcomes, portfolio_patterns,
                          raw_events, activity_events
  app/memory/            conflict_resolver, operations, retrieval, scoring, manager -
                          all deterministic; owns every state transition
  app/llm/                provider-agnostic interface + OpenAI/mock implementations
  app/agents/              thin LLM-calling wrappers, no DB writes
  app/routers/            chat, memory, graph, recommendations, decisions, activity
```

Design principle throughout (spec Sec.22): **the model proposes memory or a recommendation;
deterministic application code in `app/memory/` validates, decides the operation, and persists.**
No `save_memory()` catch-all - every write goes through an explicit `CREATE` / `UPDATE` /
`SUPERSEDE` / `PROMOTE` / `REJECT` operation in `app/memory/operations.py`.

## Production path

See spec Sec.28 (AWS/AgentCore architecture), Sec.31 (what breaks first at 200+ clients),
Sec.32 (rollout), and Sec.33 (business success metrics) - all written to be presented directly.
