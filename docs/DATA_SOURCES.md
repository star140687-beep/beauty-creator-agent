# Data sources and readiness

The repository contains 35 synthetic samples (10 products, 15 reviews, 10 content examples), **163 crowdsourced Open Beauty Facts product records across 115 brands**, five source-backed regulatory reference records, a multi-brand aggregate coverage report, and 80 labeled component evaluation cases (plus the older five-case workflow regression set). The 80 cases reuse 20 product anchors across four evaluation dimensions; they are not 80 independently sampled product records. See [evaluation protocol](EVALUATION_PROTOCOL.md). Synthetic records are for tests only and must not be presented as market evidence.

## Real local dataset

The separately supplied [Sephora Products and Skincare Reviews dataset](https://www.kaggle.com/datasets/nadyinky/sephora-products-and-skincare-reviews) is a **multi-brand retailer archive**, not a dataset limited to Sephora Collection products. It is listed by its publisher as CC BY 4.0. The local files were scanned without writing a database: **8,494 valid product listings from 304 brands and 1,092,967 valid reviews from 142 brands** passed the streaming adapter on 2026-09-15. Of these, 8,142 product listings and 1,076,043 reviews are not Sephora Collection brand records. The public [brand coverage report](../data/coverage/multibrand_coverage.json) contains aggregate counts only, never review text or reviewer information. Counts are *potential import capacity*, not a claim that the running service currently holds or has evaluated all records.

The adapter removes reviewer IDs and several common direct identifiers, keeps a stable `source_id`, and records the dataset URL/license in `source_metadata`. This is not a guarantee of complete de-identification. Product listings are third-party, unverified evidence; they do not receive official URLs or verified claims. This source spans many brands but is still **one retailer's historical review corpus**, so it cannot represent all markets or platforms. The publisher's CC BY label does not by itself resolve all third-party rights, privacy, brand, or platform terms for a commercial launch. Obtain a rights/privacy review before deploying the full review corpus.

The [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/) require attribution, a license link, and indication of changes. Do not remove dataset provenance from outputs that expose adapted content.

## Open Beauty Facts

`data/openbeautyfacts/products.jsonl` contains 163 real crowdsourced product snapshots from 115 brands with barcode, product URL, retrieval time, `source_id`, and ODbL-1.0 provenance. These are an independent product source, **not manufacturer-verified facts or approved efficacy claims**. The [Open Beauty Facts project](https://github.com/openfoodfacts/openbeautyfacts/blob/develop/README.md) describes its open, crowdsourced cosmetics database. The [official API guidance](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/) asks users to use a data dump instead of individual requests for more than a few hundred products, and to provide a custom User-Agent. Do not enlarge the current snapshot into thousands of search API calls.

## Regulatory references and product claim gap

`data/compliance/regulatory_sources.jsonl` contains five official, source-linked regulatory/guidance records for CN, US, and EU. `config/compliance_rules.yaml` contains five source-backed screening heuristics plus one clearly marked internal AI-testimony policy. The task's `market` field scopes these checks; CN is the default. See [compliance data limitations](COMPLIANCE_DATA.md). These public documents are **general requirements**, not a per-product approval database. The project still has no manufacturer-confirmed SKU claims or supporting efficacy dossiers. Product and review counts do not fill that gap.

## Reviews and platform content

No real platform post text is included in this public repository. The `ingest_authorized_content.py` adapter accepts only locally supplied, rights-cleared JSONL with a `source_url`, `source_id`, platform, category, title, body, pattern, and tone. It cannot create permission that the operator does not have.

Amazon Reviews 2023 review bodies and Chinese-platform posts are not redistributed here. The [dataset publisher's license discussion](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/discussions/1) states that it cannot assign a license to Amazon review text, so this project does not treat it as a freely redistributable production review source. Local research subsets under `data/raw/`, `data/processed/`, and `data/private/` are ignored by Git.

## Import and runtime

See [production data setup](PRODUCTION_DATA.md). The default development backend uses deterministic sample data. Set `RESEARCH_BACKEND=database` only after the PostgreSQL schema is migrated and real catalog data has been imported. The database backend excludes `source=sample` and limits individual retrieval results to the typed query limit. It currently uses indexed exact-name lookups; pgvector embedding columns exist, but semantic indexing, throughput benchmarks, and production access controls are still separate work.
