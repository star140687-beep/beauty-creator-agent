# Formal evaluation data contract

This document defines the evidence required before reporting the résumé-level
RAG + Agent evaluation. It is a collection specification, not a source of
test labels or results. Do not fill it with invented products, reviews,
platform posts, annotations, or scores.

## Preconditions

- Import only rights-cleared or public data whose source and collection date
  can be recorded.
- Keep raw documents and personally identifying review data outside Git. The
  Git repository contains only schemas, scripts, documentation, and—where
  licensing permits—small redacted examples.
- Assign a stable `source_id` to every imported Product, Review, and Content
  record, and retain provenance and licence information.
- Generate embeddings with the exact configured embedding model and store
  them in PostgreSQL + pgvector before running the formal runner.
- Freeze the case file by SHA-256 before measurement. A changed file is a new
  dataset version.

## Fixed 80-case split

The formal dataset is fixed at 80 independently labeled cases. This specifies
the required structure; it is not a claim that the cases have already been
collected or measured.

| Component | Cases | What is labeled |
| --- | ---: | --- |
| Planner / routing | 25 | Intended workflow or research intent for realistic marketing briefs. |
| Semantic retrieval | 25 | Query, metadata filters, and relevant Product, Review, or Content `source_id`s. |
| Draft grounding | 15 | Draft claims, supporting evidence IDs, and independent support labels. |
| Compliance screening | 15 | Market, draft/phrase, risk labels, and safe negative examples. |

For retrieval, deliberately include queries that do not copy the product title,
queries requiring metadata filters, ambiguous wording, and cross-brand or
cross-category distractors. Gold labels must be created without seeing the
ranked output. The 25 retrieval cases must cover Product, Review, and Content;
the internal allocation can vary as long as every retriever is represented.
The current runner validates all four cohorts but deliberately does not execute
models, database retrieval, or a benchmark in this preparation phase.

## Retrieval JSONL schema

One JSON object per line is required for each formal retrieval case:

```json
{
  "id": "review_holdout_001",
  "kind": "retrieval",
  "retriever": "review",
  "query": "dry skin users mention a non-sticky finish",
  "filters": {
    "brand": "Example Brand",
    "category": "moisturizer",
    "skin_type": "dry",
    "rating_min": 4.0
  },
  "gold_source_ids": ["licensed-review:abc123"]
}
```

`retriever` must be one of `product`, `review`, or `content`. The `query` and
optional filters are passed to the corresponding PostgreSQL + pgvector
retriever. `gold_source_ids` must refer to imported, non-sample rows. The
formal runner stops instead of returning a score when a required corpus,
embedding, or gold ID is missing.

## Reporting rules

Every formal report must preserve: dataset hash, UTC timestamp, model/provider,
case counts, numerator/denominator, failures, per-retriever results, and a
`measurement_complete` flag. A failed model or database call remains in the
denominator and is separately counted. Do not relabel lexical lookup, a fake
provider, synthetic rows, or a selected phrase list as semantic pgvector or
production performance.

## Formal case schemas

Routing rows use `kind: "routing"` with `id`, `query`, `gold_route`, optional
`metadata`, and optional `expected_workflow`. Generation rows use
`kind: "generation"` with `id`, a structured `request`,
`evidence_source_ids`, optional independently labeled `gold_claims`, and
optional `metadata`. Compliance rows use `kind: "compliance"` with `id`,
`market`, `text`, optional `gold_risk_labels`, and optional `metadata`.

The report schema reserves configurations named `single_llm`, `llm_plus_rag`,
and `full_rag_agent`. They must share the same frozen cases, corpus, model,
generation settings, and metric definitions when formally run. This repository
does not currently present any configuration as having been formally measured.
