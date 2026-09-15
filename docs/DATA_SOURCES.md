# Data Sources and Readiness

The repository contains sample data for development, real product and review datasets for retrieval, regulatory references for compliance screening, and labeled cases for offline evaluation.

Current data coverage includes:

* 35 synthetic development samples: 10 products, 15 reviews, and 10 content examples
* 163 Open Beauty Facts product records across 115 brands
* 8,494 valid multi-brand product listings
* 1,092,967 valid multi-brand reviews
* 5 source-backed regulatory reference records
* 80 labeled evaluation cases

Synthetic records are used for development and testing only. They are kept separate from real product, review, and regulatory data.

See [Evaluation Protocol](EVALUATION_PROTOCOL.md) for the evaluation setup.

## Real Local Dataset

The project supports the [Sephora Products and Skincare Reviews dataset](https://www.kaggle.com/datasets/nadyinky/sephora-products-and-skincare-reviews) as a local multi-brand product and review source.

The dataset is not limited to Sephora Collection products. The local streaming adapter identified:

* **8,494 valid product listings from 304 brands**
* **1,092,967 valid reviews from 142 brands**

Among these records, 8,142 product listings and 1,076,043 reviews belong to brands other than Sephora Collection.

Aggregate dataset coverage is stored in [`multibrand_coverage.json`](../data/coverage/multibrand_coverage.json). The report contains counts only and does not expose review text or reviewer information.

The adapter removes reviewer IDs and several common direct identifiers while retaining a stable `source_id` for evidence tracing. Dataset URL and license information are stored in `source_metadata`.

Product listings from this dataset are treated as third-party product information rather than manufacturer-verified evidence. They are not automatically assigned verified efficacy claims.

The dataset publisher lists the dataset under CC BY 4.0. The [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/) require attribution, a license link, and indication of changes when applicable. Dataset provenance is retained when adapted records are used.

## Open Beauty Facts

`data/openbeautyfacts/products.jsonl` contains **163 product records from 115 brands** collected from Open Beauty Facts.

Each record keeps provenance fields including:

* barcode
* product URL
* retrieval time
* `source_id`
* source metadata

Open Beauty Facts is a crowdsourced cosmetics database, so these records are used as product context rather than manufacturer-confirmed product evidence.

The project keeps the original source information and ODbL-1.0 provenance associated with these records.

References:

* [Open Beauty Facts](https://github.com/openfoodfacts/openbeautyfacts/blob/develop/README.md)
* [Open Food Facts API documentation](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/)

For larger imports, bulk data sources should be preferred over repeated individual API requests.

## Regulatory References

Regulatory reference data is stored in:

```text
data/compliance/regulatory_sources.jsonl
```

The current catalog contains five source-linked regulatory or guidance records covering:

* CN
* US
* EU

Executable screening rules are stored in:

```text
config/compliance_rules.yaml
```

The compliance rules use the task `market` field to select market-specific checks. `CN` is the default market.

These sources provide regulatory reference points for compliance screening. They are separate from product-specific evidence and are not treated as per-product approval records.

See [Compliance Reference Data and Limits](COMPLIANCE_DATA.md) for the compliance data setup.

## Product Evidence

Product records, ingredient lists, retailer descriptions, and consumer reviews are not treated as proof of product efficacy.

Product-specific claims require appropriate supporting evidence before they can be treated as verified Product Facts.

The project provides an authorized product intake path for adding product information together with supporting evidence:

[Production Data Setup](PRODUCTION_DATA.md#onboard-products-from-any-brand)

Evidence added through this path keeps its source information and can be used by Claim Verification and Human Review.

## Reviews and Platform Content

Review data is used primarily for Consumer Insight.

Examples include:

* recurring consumer concerns
* skin-type-related feedback
* product experience
* frequently mentioned benefits or issues

Consumer reviews are not used as direct evidence for objective product efficacy claims.

Real platform post text is not distributed in the public repository.

For authorized content, `ingest_authorized_content.py` accepts locally supplied JSONL containing fields such as:

* `source_url`
* `source_id`
* platform
* category
* title
* body
* pattern
* tone

This content is used primarily as Content Pattern evidence for generation.

Amazon Reviews 2023 and Chinese-platform post bodies are not redistributed with the repository. Local research data can be kept under:

```text
data/raw/
data/processed/
data/private/
```

These directories are excluded from Git where applicable.

## Import and Runtime

Development can run with deterministic sample data, while the database backend is used for imported product, review, and content records.

To use PostgreSQL:

```text
RESEARCH_BACKEND=database
```

The PostgreSQL schema must be migrated and the required data imported before enabling the database backend.

The retrieval layer supports the three project retrievers:

```text
Product Retriever
Review Retriever
Content Retriever
```

Depending on the request, retrieval can combine:

* Metadata Filter
* Structured Query
* Semantic Retrieval
* Top-k retrieval

Semantic Retrieval uses **PostgreSQL + pgvector** and is the retrieval path used for the formal RAG evaluation.

Retrieved records retain `source_id` and evidence metadata so they can be passed to generation, Claim Verification, and compliance review.

## Data Roles

The main data sources have different roles in the system:

| Source                      | Main Use                           | Evidence Type        |
| --------------------------- | ---------------------------------- | -------------------- |
| Product catalog             | Product information and retrieval  | Product Fact         |
| Consumer reviews            | Consumer feedback and user insight | Consumer Insight     |
| Authorized platform content | Writing and content references     | Content Pattern      |
| Regulatory references       | Compliance screening               | Regulatory Reference |
| Authorized product evidence | Product claim verification         | Official Evidence    |
| Synthetic samples           | Development and testing            | Test Data            |

Keeping these sources separate prevents consumer reviews or platform content from being used as direct substitutes for product-level factual evidence.
