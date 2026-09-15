# Evaluation Protocol

This document describes the offline evaluation setup for Beauty Creator Agent. The evaluation covers routing, retrieval, grounded generation, and compliance checking across a fixed set of 80 cases.

## 1. Evaluation Setup

The evaluation dataset is divided into four groups:

| Evaluation Task        |  Cases | Metric              |                     Result |
| ---------------------- | -----: | ------------------- | -------------------------: |
| Routing                |     25 | Routing Accuracy    |            **92% (23/25)** |
| Retrieval              |     25 | RAG Recall@5        |            **84% (21/25)** |
| Generation & Grounding |     15 | Grounded Claim Rate |     **90% (36/40 claims)** |
| Compliance & Risk      |     15 | Compliance Recall   | **94% (16/17 risk items)** |
| **Total**              | **80** |                     |                            |

Routing and retrieval are evaluated at the case level. Grounding is evaluated at the claim level, while compliance is evaluated against labeled risk items within the corresponding cases.

---

## 2. Routing Evaluation

Routing evaluation checks whether the workflow selects the correct retrieval or processing path for each request.

The cases cover product information, consumer reviews, platform content, mixed-source requests, and generation tasks that require multiple evidence sources.

The current **Routing Accuracy is 92% (23/25)**.

---

## 3. Retrieval Evaluation

Retrieval evaluation covers the three main data sources used by the system:

* Product
* Review
* Content

The retrieval layer is built on PostgreSQL and pgvector. Depending on the request, retrieval can combine Metadata Filter, Structured Query, and Semantic Retrieval.

### Product Retriever

Used for product-level information such as brand, category, ingredients, product attributes, and other structured product facts.

### Review Retriever

Searches consumer reviews and related metadata such as skin type and rating. Retrieved reviews are used to extract consumer concerns, recurring feedback, and product experience.

### Content Retriever

Searches existing platform content and provides references for content structure, tone, and platform-specific expression patterns.

### Recall@5

Recall@5 checks whether the expected evidence appears in the top five retrieved results.

The current **RAG Recall@5 is 84% (21/25)**.

The reported result is based on the PostgreSQL + pgvector retrieval path used by the current RAG pipeline.

---

## 4. Generation and Grounding

Generation evaluation checks whether generated content is supported by retrieved evidence.

A generated response may contain several factual or consumer-related claims, so grounding is evaluated at the claim level rather than treating the entire response as a single result.

The current **Grounded Claim Rate is 90% (36/40 claims)**.

A claim is considered grounded when the retrieved evidence supports the generated statement. A `source_id` alone is not treated as sufficient evidence.

---

## 5. Evidence Policy

Retrieved evidence is separated into three types.

### Product Fact

Used for factual product information such as:

* ingredients
* brand
* category
* product attributes
* structured product information

### Consumer Insight

Derived from review data and used for consumer experience and recurring feedback, including:

* common consumer concerns
* skin-type-related feedback
* frequently mentioned experience
* perceived benefits or issues

Consumer feedback is kept separate from objective product facts.

### Content Pattern

Derived from existing platform content and used as a reference for writing style, structure, and common expressions.

Content Pattern is not treated as factual evidence for product claims.

---

## 6. Source Traceability

Generated content keeps `source_ids` for evidence tracing.

```text
Generated Claim
    ↓
source_id
    ↓
Retrieved Evidence
    ↓
Evidence Type
```

Evidence types include Product Fact, Consumer Insight, and Content Pattern.

This allows claims to be traced back to their supporting context during verification and review.

---

## 7. Compliance and Risk Evaluation

Compliance evaluation checks whether risky, unsupported, or inappropriate claims are identified before content is returned.

A compliance case may contain more than one labeled risk item. The current **Compliance Recall is 94% (16/17 risk items)**.

The compliance flow includes:

### Rule Engine

Handles risks that can be identified through explicit rules and patterns.

### Claim Verification

Checks whether factual statements are supported by retrieved evidence and whether the evidence type is appropriate for the claim.

### Semantic Review

Handles cases that require contextual judgment and cannot be reliably covered by simple keyword or rule matching.

Content that still requires manual judgment can be sent to Human Review.

---

## 8. Baseline Comparison

Three controlled configurations are used for comparison.

### Single LLM

```text
User Input
    ↓
LLM
    ↓
Generated Content
```

Content is generated directly from the request without retrieval or evidence verification.

### LLM + RAG

```text
User Input
    ↓
Retrieval
    ↓
LLM
    ↓
Generated Content
```

Relevant context is retrieved before generation, without the complete Agent verification and compliance flow.

### Full RAG + Agent

```text
User Input
    ↓
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

This configuration represents the complete Beauty Creator Agent workflow.

The baseline configurations are used to compare the effect of retrieval, evidence verification, and compliance checking within the same project.

---

## 9. Evaluation Results

| Metric              |                     Result |
| ------------------- | -------------------------: |
| Routing Accuracy    |            **92% (23/25)** |
| RAG Recall@5        |            **84% (21/25)** |
| Grounded Claim Rate |     **90% (36/40 claims)** |
| Compliance Recall   | **94% (16/17 risk items)** |

The evaluation uses 80 cases in total:

* 25 Routing cases
* 25 Retrieval cases
* 15 Generation & Grounding cases
* 15 Compliance & Risk cases

---

## 10. Reproducibility

The evaluation dataset is frozen for each run.

Evaluation reports record:

* dataset version
* dataset SHA-256
* provider and model
* evaluation timestamp
* total number of cases
* cases per evaluation group
* metric results
* failed calls or invalid cases
* per-case outcomes

Failed retrieval or model calls are recorded in the evaluation output rather than silently removed.

---

## 11. Legacy Benchmark

An earlier v2 component benchmark is retained for regression and smoke testing.

It contains:

* 20 Routing cases
* 20 Product Lookup cases
* 20 Claim / Evidence cases
* 20 Marketing Risk cases

The legacy benchmark uses lexical or token-overlap matching in parts of the retrieval evaluation. It is separate from the current RAG evaluation and is not used for the reported RAG Recall@5.

---

## 12. Scope

The evaluation is an offline benchmark for the current project implementation. It is used to compare changes to routing, retrieval, generation, grounding, and compliance components under a fixed evaluation set.

Current results:

* **Routing Accuracy: 92% (23/25)**
* **RAG Recall@5: 84% (21/25)**
* **Grounded Claim Rate: 90% (36/40 claims)**
* **Compliance Recall: 94% (16/17 risk items)**