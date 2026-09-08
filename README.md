# Beauty Creator Agent

Evidence-grounded beauty content generation with LangGraph, FastAPI, PostgreSQL/pgvector, local Ollama models, compliance checks, bounded revision, and human review.

## Overview

The workflow accepts a product brief, plans the required research, retrieves traceable product/review/content evidence, writes platform content, performs layered compliance checks, revises failures at most twice, then pauses for human approval, editing, or rejection.

The default local model is `qwen2.5:14b` served by Ollama. Automated tests use `FakeLLMProvider` and do not require a model, API key, database, or paid service.

## Agent workflow

```text
Request → Planner → Research Tools → Evidence → Writer → Compliance
                                                    ↑          │
                                                    └─ Revision┘ (max 2)
                                                               ↓
                                                     Human Review → Final
```

## Data and evidence policy

- Product facts, consumer observations, content patterns, and trends remain distinct.
- Retrieved evidence retains a stable `source_id`.
- Product claims without resolvable evidence fail compliance.
- Category insights cannot be presented as feedback about the current product.
- Retrieved documents are untrusted data, never instructions.
- Sample data is synthetic and must not be presented as market evidence.
- The repository includes a small ODbL-licensed Open Beauty Facts product snapshot with per-record provenance. It remains crowdsourced evidence, not manufacturer verification.

## Tech stack

- Python 3.12, uv, Pydantic 2
- LangGraph with checkpointed HITL
- Ollama `qwen2.5:14b` with schema-constrained output
- FastAPI and Server-Sent Events
- PostgreSQL 16, pgvector, SQLAlchemy, Alembic
- Streamlit demo UI
- pytest, Ruff, mypy, GitHub Actions

## Quick start

```powershell
conda activate agent
uv sync
Copy-Item .env.example .env
uv run uvicorn beauty_creator_agent.main:app --reload --app-dir src
```

In another terminal:

```powershell
conda activate agent
uv run streamlit run frontend/app.py
```

Open `http://127.0.0.1:8501`. Ollama must be running at `http://127.0.0.1:11434` with `qwen2.5:14b` available.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/v1/tasks` | Create and start a workflow |
| `GET` | `/v1/tasks/{task_id}` | Read status, state, evidence and draft |
| `GET` | `/v1/tasks/{task_id}/history` | Read workflow event history |
| `GET` | `/v1/tasks/{task_id}/stream` | Consume SSE progress events |
| `POST` | `/v1/tasks/{task_id}/review` | Approve, edit or reject a paused draft |
| `GET` | `/health` | API liveness |

## Database

```powershell
docker compose up -d postgres
uv run alembic upgrade head
uv run python scripts/ingest_samples.py
```

The ingestion command upserts by `source_id`, so repeated runs do not duplicate sample records.

Refresh the licensed real-product snapshot with:

```powershell
uv run python scripts/download_openbeautyfacts.py --per-category 5
```

See `docs/DATA_SOURCES.md` for attribution and the local-only review import policy.

## Docker

```powershell
docker compose up --build
```

Services:

- API: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:8501`
- PostgreSQL: `127.0.0.1:5432`

The API container reaches the host Ollama service through `host.docker.internal`.

## Evaluation

Evaluation is separate from the production workflow and operates on fixed JSONL cases:

```powershell
uv run python -m beauty_creator_agent.evaluation.runner
```

It writes `evaluation/report.json` and `evaluation/report.csv` with planner accuracy, forbidden-claim absence, compliance completion, HITL reachability, and provenance coverage.

## Quality checks

```powershell
uv run pytest
uv run ruff check src tests scripts migrations frontend
uv run mypy src tests
```

## Publish to GitHub safely

Before the first commit, create a local environment file and replace the database password:

```powershell
Copy-Item .env.example .env
# Edit .env locally. It is ignored by Git.
```

Then run the release gates and inspect exactly what will be committed:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src tests
git status --short
git add .
git diff --cached --stat
git diff --cached -- . ':!data/openbeautyfacts/products.jsonl' ':!uv.lock'
```

Do not stage `.env`, raw/processed/private datasets, database dumps, private keys, or evaluation reports. CI performs an additional Gitleaks scan and uses the fake model provider, so GitHub needs no model API key.

After reviewing the staged diff:

```powershell
git commit -m "feat: initial Beauty Creator Agent MVP"
git remote add origin https://github.com/YOUR_NAME/YOUR_REPOSITORY.git
git push -u origin main
```

## Project structure

```text
src/beauty_creator_agent/
├── agents/       # Fake and Ollama model providers
├── api/          # HTTP and SSE transport
├── core/         # Settings, logging, errors and safety
├── db/           # SQLAlchemy models and repositories
├── evaluation/   # Independent evaluation runner
├── graph/        # LangGraph state, nodes and routing
├── rag/          # Embedding abstraction
├── schemas/      # Pydantic contracts
├── services/     # Research, compliance, ingestion and task orchestration
└── tools/        # Typed product/review/content tools
```

## Current limitations and roadmap

- Local development defaults to in-memory checkpoints. Docker enables PostgreSQL checkpoints, allowing a waiting thread to be recovered by `task_id` after an API process restart.
- The included sample retriever is deterministic lexical search. pgvector models and Ollama embeddings are ready for a database-backed retriever adapter.
- Trend research is optional and disabled by default.
- Sample data is intentionally small and synthetic.
