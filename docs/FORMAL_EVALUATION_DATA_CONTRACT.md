# Formal Evaluation Data Contract

This document defines the data structure and evidence requirements used by the formal Beauty Creator Agent evaluation.

The formal evaluation uses a frozen set of **80 labeled cases** covering routing, semantic retrieval, grounded generation, and compliance screening. Results and metric definitions are documented in [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md).

## Preconditions

* Use rights-cleared or public data with recorded source and collection metadata.
* Keep raw documents and personally identifying review data outside Git.
* Assign a stable `source_id` to imported Product, Review, and Content records.
* Retain source provenance and license information where applicable.
* Generate embeddings with the configured embedding model and store them in PostgreSQL + pgvector.
* Freeze the evaluation case file by SHA-256 before each formal run.
* Treat any change to the frozen case file as a new dataset version.

## Fixed 80-Case Split

The formal dataset contains 80 labeled cases:

| Component              |  Cases | Label                                             |
| ---------------------- | -----: | ------------------------------------------------- |
| Planner / Routing      |     25 | Expected route or workflow                        |
| Semantic Retrieval     |     25 | Query, filters, and relevant `source_id`s         |
| Generation & Grounding |     15 | Claims, supporting evidence, and grounding labels |
| Compliance & Risk      |     15 | Market, risk items, and expected screening labels |
| **Total**              | **80** |                                                   |

The retrieval cases cover Product, Review, and Content retrieval.

They include semantic queries, metadata-filtered queries, ambiguous wording, and distractor records so that retrieval is evaluated against the PostgreSQL + pgvector path rather than simple title or token matching.

Gold labels are stored independently from ranked retrieval output.

## Retrieval JSONL Schema

Each retrieval case follows this structure:

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
  "gold_source_ids": [
    "licensed-review:abc123"
  ]
}
```

`retriever` must be one of:

```text
product
review
content
```

The query and optional filters are passed to the corresponding retriever.

`gold_source_ids` refer to evidence records available in the evaluation corpus. Missing required corpus data, embeddings, or gold evidence IDs are recorded as evaluation failures rather than silently excluded.

## Routing Schema

Routing cases use `kind: "routing"`.

Example:

```json
{
  "id": "routing_001",
  "kind": "routing",
  "query": "Find feedback from dry-skin users about this moisturizer",
  "gold_route": "review",
  "metadata": {
    "category": "moisturizer"
  }
}
```

Routing fields include:

* `id`
* `query`
* `gold_route`
* optional `metadata`
* optional `expected_workflow`

Routing Accuracy is calculated across the 25 routing cases.

The current formal result is **92% (23/25)**.

## Generation and Grounding Schema

Generation cases use `kind: "generation"`.

Example:

```json
{
  "id": "generation_001",
  "kind": "generation",
  "request": {
    "product_name": "Example Product",
    "platform": "social",
    "market": "CN"
  },
  "evidence_source_ids": [
    "product:example001",
    "review:example002"
  ],
  "gold_claims": [],
  "metadata": {}
}
```

Generation fields include:

* `id`
* structured `request`
* `evidence_source_ids`
* optional `gold_claims`
* optional `metadata`

The 15 Generation & Grounding cases are evaluated at the claim level because one generated response may contain multiple independently verifiable claims.

The current formal result is **90% Grounded Claim Rate (36/40 claims)**.

## Compliance Schema

Compliance cases use `kind: "compliance"`.

Example:

```json
{
  "id": "compliance_001",
  "kind": "compliance",
  "market": "CN",
  "text": "Example generated content",
  "gold_risk_labels": [],
  "metadata": {}
}
```

Compliance fields include:

* `id`
* `market`
* `text`
* optional `gold_risk_labels`
* optional `metadata`

A compliance case may contain more than one independently labeled risk item.

The current formal result is **94% Compliance Recall (16/17 risk items)**.

## Reporting Rules

Each formal evaluation report records:

* dataset version
* dataset SHA-256
* UTC timestamp
* provider and model
* total case count
* cases per evaluation group
* metric numerator and denominator
* per-retriever results
* failed model or database calls
* per-case outcomes
* `measurement_complete`

Failed retrieval, model, or evaluation calls are recorded rather than silently removed from the evaluation output.

Formal RAG results use the PostgreSQL + pgvector retrieval path. Lexical lookup, synthetic smoke tests, and the legacy component benchmark are kept separate from the reported semantic retrieval results.

## Evaluation Configurations

The evaluation supports three controlled configurations:

```text
single_llm
llm_plus_rag
full_rag_agent
```

### `single_llm`

Generation without retrieval or Agent verification.

### `llm_plus_rag`

Generation with retrieved context but without the complete Agent verification and compliance flow.

### `full_rag_agent`

The complete workflow:

```text
Routing
  ↓
Retrieval
  ↓
Generation
  ↓
Evidence Verification
  ↓
Risk Review
  ↓
Final Output / Human Review
```

Controlled comparisons use the same frozen evaluation data and consistent metric definitions.

## Current Formal Results

| Metric              |                     Result |
| ------------------- | -------------------------: |
| Routing Accuracy    |            **92% (23/25)** |
| RAG Recall@5        |            **84% (21/25)** |
| Grounded Claim Rate |     **90% (36/40 claims)** |
| Compliance Recall   | **94% (16/17 risk items)** |

The dataset contains:

```text
25 Routing
25 Retrieval
15 Generation & Grounding
15 Compliance & Risk
--------------------------
80 Total Cases
```

The formal results correspond to the frozen evaluation dataset and current project implementation. Legacy lexical and workflow regression tests are maintained separately and are not included in these reported metrics.
