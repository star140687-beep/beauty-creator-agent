# Beauty Creator Agent

Evidence-grounded beauty content generation with LangGraph, FastAPI, PostgreSQL + pgvector, local Ollama models, compliance checks, bounded revision, and human review.

## Overview

Beauty Creator Agent is a RAG + Agent workflow for beauty content generation.

The system accepts a product brief, plans the required research, retrieves product, review, and content evidence, generates platform content, verifies claims, performs compliance checks, and routes unresolved cases to human review.

The default local setup uses `qwen2.5:14b` for writing and `llama3.2:3b` for planner and compliance steps, served by Ollama. Automated tests use `FakeLLMProvider` and do not require a model, API key, database, or paid service.

## Agent Workflow

```text
Request → Planner → Research Tools → Evidence → Writer → Compliance
                                                ↑          │
                                                └─ Revision┘ (max 1 by default)
                                                           ↓
                                                  Human Review → Final
```

The main workflow includes:

* request planning and routing
* Product / Review / Content retrieval
* evidence-grounded generation
* claim verification
* compliance and risk screening
* bounded revision
* human approval, editing, or rejection

## Data and Evidence Policy

Product facts, consumer insights, and content patterns are handled as separate evidence types.

* **Product Fact** — structured product information and supported product claims
* **Consumer Insight** — observations derived from consumer reviews
* **Content Pattern** — platform content used for writing structure and expression
* **Official Evidence** — documented product evidence used for claim verification

Retrieved evidence retains a stable `source_id` for traceability.

Product claims without supporting evidence fail Claim Verification. Consumer reviews and Content Pattern records are not used as substitutes for product-level factual evidence.

The repository also includes:

* 163 Open Beauty Facts product records from 115 brands
* a local multi-brand dataset with 8,494 valid product listings from 304 brands
* 1,092,967 valid reviews from 142 brands
* five linked CN / US / EU regulatory reference records
* market-scoped compliance screening rules
* 80 labeled formal evaluation cases

Synthetic sample data is used for development and testing only.

See:

* [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)
* [`docs/COMPLIANCE_DATA.md`](docs/COMPLIANCE_DATA.md)
* [`docs/PRODUCTION_DATA.md`](docs/PRODUCTION_DATA.md)
* [`docs/EVALUATION_PROTOCOL.md`](docs/EVALUATION_PROTOCOL.md)

## Tech Stack

* Python 3.12
* uv
* Pydantic 2
* LangGraph
* FastAPI
* Server-Sent Events
* PostgreSQL 16
* pgvector
* SQLAlchemy
* Alembic
* Ollama `qwen2.5:14b`
* Streamlit
* pytest
* Ruff
* mypy
* GitHub Actions

## Quick Start

```powershell
conda activate agent

uv sync

Copy-Item .env.example .env

uv run uvicorn beauty_creator_agent.main:app --reload --app-dir src
```

Start the Streamlit interface in another terminal:

```powershell
conda activate agent

uv run streamlit run frontend/app.py
```

Open:

```text
http://127.0.0.1:8501
```

For local LLM generation, Ollama should be running at:

```text
http://127.0.0.1:11434
```

with `qwen2.5:14b` available.

## API

| Method | Endpoint                      | Purpose                                |
| ------ | ----------------------------- | -------------------------------------- |
| `POST` | `/v1/tasks`                   | Create and start a workflow            |
| `GET`  | `/v1/tasks/{task_id}`         | Read status, state, evidence and draft |
| `GET`  | `/v1/tasks/{task_id}/history` | Read workflow event history            |
| `GET`  | `/v1/tasks/{task_id}/stream`  | Consume SSE progress events            |
| `POST` | `/v1/tasks/{task_id}/review`  | Approve, edit or reject a paused draft |
| `GET`  | `/health`                     | API liveness                           |

## Database

Start PostgreSQL and run the migrations:

```powershell
docker compose up -d postgres

uv run alembic upgrade head
```

Sample records can be imported with:

```powershell
uv run python scripts/ingest_samples.py
```

The ingestion command upserts records by `source_id`, so repeated runs do not create duplicate sample records.

The Open Beauty Facts snapshot can be refreshed with:

```powershell
uv run python scripts/download_openbeautyfacts.py --per-category 50
```

For real local data, enable the database backend after migration and import:

```text
RESEARCH_BACKEND=database
```

See [`docs/PRODUCTION_DATA.md`](docs/PRODUCTION_DATA.md) for staged PostgreSQL imports and additional product/content onboarding.

## Retrieval

The RAG layer contains three typed retrievers:

* Product Retriever
* Review Retriever
* Content Retriever

Depending on the request, retrieval can combine:

* Metadata Filter
* Structured Query
* Semantic Retrieval
* Top-k retrieval

Semantic Retrieval uses **PostgreSQL + pgvector**.

Retrieved records retain `source_id` and evidence metadata so that evidence can be traced through generation, Claim Verification, and compliance review.

## Compliance

The compliance layer combines:

```text
Generated Content
      ↓
Rule Engine
      ↓
Claim Verification
      ↓
Claim-Coverage Screening
      ↓
Semantic Review
      ↓
Pass / Revision / Human Review
```

Market-specific screening currently supports:

* `CN`
* `US`
* `EU`

The regulatory references are used for screening and provenance. Product-specific efficacy and safety claims still require appropriate supporting evidence and human review where necessary.

See [`docs/COMPLIANCE_DATA.md`](docs/COMPLIANCE_DATA.md) for source and evidence details.

## Docker

Run the full local stack with:

```powershell
docker compose up --build
```

Services:

* API: `http://127.0.0.1:8000`
* Frontend: `http://127.0.0.1:8501`
* PostgreSQL: `127.0.0.1:5432`

The API container reaches the host Ollama service through `host.docker.internal`.

## Evaluation

The formal offline evaluation contains **80 labeled cases**:

| Evaluation Task        |  Cases | Metric              |                     Result |
| ---------------------- | -----: | ------------------- | -------------------------: |
| Routing                |     25 | Routing Accuracy    |            **92% (23/25)** |
| Retrieval              |     25 | RAG Recall@5        |            **84% (21/25)** |
| Generation & Grounding |     15 | Grounded Claim Rate |     **90% (36/40 claims)** |
| Compliance & Risk      |     15 | Compliance Recall   | **94% (16/17 risk items)** |
| **Total**              | **80** |                     |                            |

The retrieval benchmark uses the PostgreSQL + pgvector Semantic Retrieval path.

Grounding is evaluated at the claim level because one generation case may contain multiple factual claims. Compliance is evaluated against independently labeled risk items.

The evaluation supports three controlled configurations:

* `single_llm`
* `llm_plus_rag`
* `full_rag_agent`

Formal reports record the dataset version, SHA-256, model/provider, case outcomes, metric counts, and failures.

See [`docs/EVALUATION_PROTOCOL.md`](docs/EVALUATION_PROTOCOL.md) for metric definitions and evaluation details.

The older component and workflow benchmarks remain available for regression and smoke testing and are kept separate from the formal results.

## Quality Checks

```powershell
uv run pytest

uv run ruff check src tests scripts migrations frontend

uv run mypy src tests
```

## Publish to GitHub Safely

Create the local environment file before running the project:

```powershell
Copy-Item .env.example .env
```

Keep `.env` and database credentials outside Git.

Before committing:

```powershell
uv run pytest

uv run ruff check .

uv run mypy src tests

git status --short

git add .

git diff --cached --stat

git diff --cached -- . ':!data/openbeautyfacts/products.jsonl' ':!uv.lock'
```

Do not commit:

* `.env`
* raw datasets
* processed private datasets
* database dumps
* private keys
* private product documents
* generated evaluation reports

CI uses the fake model provider and does not require a model API key.

After reviewing the staged files:

```powershell
git commit -m "feat: initial Beauty Creator Agent MVP"

git remote add origin https://github.com/YOUR_NAME/YOUR_REPOSITORY.git

git push -u origin main
```

## Project Structure

```text
src/beauty_creator_agent/
├── agents/       # Fake and Ollama model providers
├── api/          # HTTP and SSE transport
├── core/         # Settings, logging, errors and safety
├── db/           # SQLAlchemy models and repositories
├── evaluation/   # Evaluation runners and metrics
├── graph/        # LangGraph state, nodes and routing
├── rag/          # Embeddings and retrieval
├── schemas/      # Pydantic contracts
├── services/     # Research, compliance, ingestion and task orchestration
└── tools/        # Typed product/review/content tools
```

## Current Limitations

* Local development defaults to in-memory checkpoints. Docker can use PostgreSQL-backed checkpoints for workflow recovery.
* Real-data coverage depends on the datasets imported into the local PostgreSQL instance.
* Product and review data from crowdsourced or retailer sources are not treated as manufacturer-verified efficacy evidence.
* Real platform content requires separately supplied, rights-cleared source data.
* Product-specific efficacy and safety claims require appropriate supporting evidence and may be routed to Human Review.
* Regulatory screening rules support the current CN, US, and EU reference set and should be maintained as source requirements change.
* Trend research is optional and disabled by default.
* The 80-case benchmark is an offline evaluation of the current workflow; production monitoring, throughput testing, and data governance are handled separately.
