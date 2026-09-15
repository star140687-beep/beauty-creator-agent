# Real-data import guide

This guide follows the tutorial's stage 5 (normalize and import) and stage 6 (separate typed retrievers). It is an engineering path toward scale, **not a production certification**.

## Capacity verified locally

The supplied multi-brand retailer CSV files were stream-validated on 2026-09-15: 8,494 product listings from 304 brands and 1,092,967 reviews from 142 brands. The repository also includes 163 Open Beauty Facts records from 115 brands. Counting required no database and did not publish raw reviews. Full import size and time are not yet measured. The review file alone is about 542 MB; allow substantially more disk space for PostgreSQL tables, indexes, WAL, and backups.

## Prepare PostgreSQL

Use a private database with a strong local password in `.env`. Never upload raw review files or a database dump to GitHub.

```powershell
docker compose up -d postgres
uv run alembic upgrade head
```

The Docker daemon must be running. Migrations should finish before importing.

## Validate, then import in batches

Replace the two paths below with your local dataset paths. The first command does not write to PostgreSQL.

```powershell
uv run python scripts/ingest_sephora.py --products "C:\path\to\product_info.csv" --reviews "C:\path\to\Skincare Reviews.csv" --limit-reviews 2000 --dry-run
uv run python scripts/ingest_sephora.py --products "C:\path\to\product_info.csv" --reviews "C:\path\to\Skincare Reviews.csv" --limit-reviews 2000
```

After checking retrieval and data rights, increase `--limit-reviews` in stages (for example 20,000, then 100,000). Use `--all-reviews` only when the operator has approved full-corpus storage. The importer reads CSV rows one by one, upserts by `source_id`, deduplicates each batch, and commits every 500 rows by default. Reruns update records instead of creating duplicates. Partial imports remain committed; rerun after a failure.

## Use the database catalog

Set `RESEARCH_BACKEND=database` in your **local** `.env` after migration/import, then restart the API. This backend searches real products and reviews by exact product name, looks up content patterns by the matched product category and platform, uses typed limits, and excludes synthetic sample rows. It does not yet provide fuzzy product matching or full pgvector RAG; a different spelling may yield no match.

```powershell
RESEARCH_BACKEND=database
```

`RESEARCH_BACKEND=sample` remains the default for reproducible tests and offline development. Docker's API service uses the database backend.

## Platform content

Supply your own rights-cleared JSONL under `data/private/`. Each line must contain `source_id`, `source_url`, `platform`, `category`, `title`, `body`, `content_pattern`, and `tone`; `hashtags` is optional. Do not put real usernames, contact details, or unlicensed copied posts into Git.

```powershell
uv run python scripts/ingest_authorized_content.py data/private/owned_content.jsonl --source-name brand_owned --license owned --dry-run
uv run python scripts/ingest_authorized_content.py data/private/owned_content.jsonl --source-name brand_owned --license owned
```

This import path does not verify rights independently; the operator must document the grant and retention period. Without authorized platform content, the database content retriever correctly returns no real examples.

## Onboard products from any brand

The service is brand-agnostic, but the two current public/local datasets are not a complete world catalog. For another brand, supply a rights-cleared local JSONL file with `source_id`, `brand`, `name`, `category`, `description`, and `source_url`; `ingredients` is optional. The generic importer marks unverified third-party records as such and **rejects efficacy claims by default**.

```powershell
uv run python scripts/ingest_authorized_products.py data/private/brand_products.jsonl --source-name brand_catalog --license owned --dry-run
```

Only when an authorized operator has checked the brand's actual documentation, each `claims` entry may be paired with an exact `claim_evidence` URL mapping and imported with `--manufacturer-documented`. This marks an operator-confirmed manufacturer document, **not a regulatory approval**. The linked document and claim wording still require a human adequacy/legal review. Never commit private documents or unlicensed brand catalog text.

## Before any public launch

- Review dataset/third-party rights, privacy, attribution, and deletion handling.
- Add API authentication and role-based access to review text and task history.
- Benchmark import time, storage, exact-name query p95 latency, and concurrent workflow load with the actual database.
- Build a separate verified manufacturer product-knowledge source for factual claims.
- Add semantic retrieval/indexing if fuzzy or concept-level search is required.
- Evaluate representative real-data retrieval quality and compliance; the current 5-case evaluation set is not enough for a launch claim.
