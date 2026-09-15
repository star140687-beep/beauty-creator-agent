# Real-Data Import Guide

This guide covers local data validation, PostgreSQL import, and the setup of Product, Review, and Content retrievers.

## Data Capacity

The local multi-brand retailer dataset contains:

* **8,494 product listings from 304 brands**
* **1,092,967 reviews from 142 brands**
* **163 Open Beauty Facts product records from 115 brands**

The source files can be validated before database import. Raw review data and database dumps should remain outside the public repository.

For large imports, allow additional disk space for PostgreSQL tables, pgvector indexes, WAL, and backups.

## Prepare PostgreSQL

Use a private PostgreSQL instance and keep database credentials in the local `.env` file.

```powershell
docker compose up -d postgres

uv run alembic upgrade head
```

The Docker daemon must be running and database migrations should complete before importing data.

## Validate and Import

Replace the paths below with the local dataset paths.

Run a dry check first:

```powershell
uv run python scripts/ingest_sephora.py --products "C:\path\to\product_info.csv" --reviews "C:\path\to\Skincare Reviews.csv" --limit-reviews 2000 --dry-run
```

Then import the validated batch:

```powershell
uv run python scripts/ingest_sephora.py --products "C:\path\to\product_info.csv" --reviews "C:\path\to\Skincare Reviews.csv" --limit-reviews 2000
```

For larger imports, increase `--limit-reviews` in stages, for example:

```text
2,000
20,000
100,000
```

Use `--all-reviews` when a full-corpus import is required and storage of the complete dataset has been approved.

The importer:

* reads CSV records incrementally
* assigns stable `source_id` values
* upserts existing records
* deduplicates records within each batch
* commits in batches of 500 rows by default

Rerunning the importer updates matching records instead of creating duplicates. If an import stops partway through, committed batches remain available and the importer can be run again.

## Database Backend

After migration and import, enable the database backend in the local `.env`:

```text
RESEARCH_BACKEND=database
```

Restart the API after changing the backend.

For reproducible tests and offline development, the sample backend remains available:

```text
RESEARCH_BACKEND=sample
```

The database backend excludes synthetic sample rows from real-data retrieval.

## Retrieval

The database backend provides separate retrievers for:

```text
Product Retriever
Review Retriever
Content Retriever
```

The retrieval pipeline can combine:

* Metadata Filter
* Structured Query
* Semantic Retrieval
* Top-k retrieval

Semantic Retrieval uses **PostgreSQL + pgvector** with stored embeddings.

Product, Review, and Content records retain their `source_id` and source metadata so retrieved evidence can be traced through generation and verification.

The same PostgreSQL + pgvector retrieval path is used by the formal RAG evaluation described in [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md).

## Platform Content

Real platform content should be supplied as rights-cleared JSONL under `data/private/`.

Each record contains:

* `source_id`
* `source_url`
* `platform`
* `category`
* `title`
* `body`
* `content_pattern`
* `tone`
* optional `hashtags`

Validate the file first:

```powershell
uv run python scripts/ingest_authorized_content.py data/private/owned_content.jsonl --source-name brand_owned --license owned --dry-run
```

Then import:

```powershell
uv run python scripts/ingest_authorized_content.py data/private/owned_content.jsonl --source-name brand_owned --license owned
```

The operator is responsible for documenting the source, usage rights, and retention requirements for imported content.

Without authorized platform content, the Content Retriever does not substitute synthetic or unrelated content as real platform evidence.

## Onboard Products from Any Brand

The product pipeline is brand-agnostic. Additional product catalogs can be imported from rights-cleared local JSONL files.

Each product record contains:

* `source_id`
* `brand`
* `name`
* `category`
* `description`
* `source_url`
* optional `ingredients`

Run validation before import:

```powershell
uv run python scripts/ingest_authorized_products.py data/private/brand_products.jsonl --source-name brand_catalog --license owned --dry-run
```

Unverified third-party product records are not automatically treated as verified efficacy evidence.

## Product Claim Evidence

When manufacturer documentation is available, a product claim can be paired with a corresponding `claim_evidence` URL.

An authorized operator can then import the documented product record using:

```text
--manufacturer-documented
```

This marks the evidence as operator-confirmed manufacturer documentation within the project. It does not represent regulatory approval.

Product claims and supporting documents remain available for Claim Verification and Human Review.

Private documents and restricted brand catalog material should remain outside the public repository.

## Evidence Types

Imported data is separated by evidence role:

| Data                        | Evidence Role           |
| --------------------------- | ----------------------- |
| Product catalog             | Product Fact            |
| Consumer reviews            | Consumer Insight        |
| Authorized platform content | Content Pattern         |
| Manufacturer documentation  | Official Evidence       |
| Regulatory references       | Compliance Reference    |
| Synthetic records           | Development / Test Data |

Reviews and Content Pattern records are not used as substitutes for official product evidence.

## Evaluation

The current formal offline evaluation uses **80 labeled cases**:

* 25 Routing
* 25 Retrieval
* 15 Generation & Grounding
* 15 Compliance & Risk

Current results are:

| Metric              |                     Result |
| ------------------- | -------------------------: |
| Routing Accuracy    |            **92% (23/25)** |
| RAG Recall@5        |            **84% (21/25)** |
| Grounded Claim Rate |     **90% (36/40 claims)** |
| Compliance Recall   | **94% (16/17 risk items)** |

See [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md) for the full evaluation setup.

## Deployment Checklist

Before using a larger real-data corpus:

* review dataset rights, privacy, attribution, and retention requirements
* keep credentials and private source data outside Git
* configure API authentication and access control for private data
* monitor PostgreSQL and pgvector storage as the corpus grows
* benchmark import time, retrieval latency, and concurrent workflow load on the target environment
* maintain manufacturer-supported evidence for product-specific efficacy or safety claims
* keep regulatory references and market-specific screening rules current
* review flagged or insufficiently supported claims through the Human Review path

The formal offline benchmark measures the current retrieval, grounding, and compliance workflow. Production monitoring and data governance remain separate from offline evaluation.
