# Evaluation protocol

## Formal RAG + Agent evaluation status

The project is implementing a separate formal evaluation path for the résumé's
Product / Review / Content retrieval design. Its main retrieval metric must run
the PostgreSQL + pgvector retrievers (`semantic_search_products`,
`semantic_search_reviews`, and `semantic_search_content`) using an embedding
model and a private, rights-cleared labeled corpus. The runner refuses to issue
a formal metric if any retriever has no non-sample embedded rows, a gold
`source_id` is missing, or a retrieval call fails.

Current status: **formal evaluation pending environment and data**. The current
workspace has no `.env`, no reachable PostgreSQL instance, no configured
embedding model, and no imported real/authorized review or platform-content
corpus. Therefore there is no formal pgvector Recall@5, whole-draft groundedness
score, or full RAG + Agent baseline result to report yet. The existing v2 set
below is retained only as a lexical component regression benchmark; its scores
are not the résumé's semantic-RAG performance.

To enable formal measurement, provide a private JSONL case file with Product,
Review, and Content retrieval cases; each case must specify a semantic query,
metadata filters, and one or more gold `source_id` values. Import the matching
rights-cleared corpus, generate/store embeddings, set `RESEARCH_BACKEND=database`
and `EMBEDDING_MODEL`, then run the database preflight. Formal reports must list
per-retriever numerator, denominator, failures, model, dataset hash, timestamp,
and measurement completeness.

The currently implemented formal command measures the retrieval portion only:

```powershell
uv run python -m beauty_creator_agent.evaluation.formal_runner data/private/formal_retrieval_cases.jsonl
```

Its input contract and the fixed 25/25/15/15 80-case split are documented in
[`FORMAL_EVALUATION_DATA_CONTRACT.md`](FORMAL_EVALUATION_DATA_CONTRACT.md).
The command validates the formal dataset only in this phase; it does not run a
model, database retrieval, or benchmark and cannot be presented as a
full-system result.

## Legacy lexical component benchmark (v2)

`evaluation/datasets/v2.jsonl` has 80 labeled **component** cases: 20 routing briefs, 20 product lookups, 20 fixed claim/evidence pairs, and 20 marketing-risk phrases. The product anchors are 20 Open Beauty Facts records; the risk phrases and gold labels were authored for this project. They are not 80 independent product records, a random production sample, or legal determinations. Dataset creation is reproducible with `uv run python scripts/build_evaluation_cases.py`.

Run the real local model, after starting Ollama and downloading `qwen2.5:14b`:

```powershell
uv run python -m beauty_creator_agent.evaluation.runner_v2 --provider ollama --model qwen2.5:14b
```

The ignored `evaluation/report.json` records model, dataset SHA-256, UTC time, every case's compact outcome, count denominators, and call failures. `measurement_complete` is true only for a full 80-case Ollama run with zero failed calls. `--limit-per-kind 2` is a smoke test of 8 cases, **not** the full 80-case result. `--provider fake` is only a deterministic test-double check; its percentages must never be cited as model performance. The old v1 five-case runner remains for workflow regression checks and no longer writes invented baseline scores.

## Definitions

| Measure | Numerator / denominator | Scope |
| --- | --- | --- |
| Routing Accuracy | correct intent / 20 routing briefs | Planner model; the same planner decision is reused across ablations. |
| RAG Recall@5 | gold product `source_id` in top five / 20 lookups | In-memory catalog uses token overlap. This is **lexical product lookup**, not pgvector semantic retrieval or recall over the million-row archive. Single LLM has no retrieval by design. |
| Fixed Claim Verification Accuracy | correct supported/unsupported decision / 20 fixed pairs | Deterministic provenance verifier only; not a Qwen claim-classification score. No counterpart is reported for ablations without this verifier. |
| Grounded Claim Rate | directly supported non-identity factual claims / all non-identity factual claims | Counts `product_fact` and `consumer_observation` but excludes the trivial `产品名称为…` claim. The verifier checks direct evidence relevance, not mere `source_id` presence. If no substantive claims are emitted, this is `null`, not 100%. This is a **pre-compliance draft** measure. |
| Identity-inclusive grounded rate | all directly supported factual claims / all factual claims | Diagnostic only; a name-only draft can score 100% here without any substantive product evidence. Do not use this rate as the résumé's Grounded Claim Rate. |
| Compliance Recall | risk phrases flagged / 12 labeled risky phrases | Negative cases (8) also produce precision/specificity. A service error is counted, not silently dropped; neither a fail-closed system error nor legal uncertainty is a true risk detection. |

## Controlled ablations

- `single_llm`: same planner, writer without evidence, no product lookup, model-only semantic risk review.
- `llm_plus_rag`: same planner, writer with user-name and crowdsourced product evidence, lexical product lookup, model-only semantic risk review.
- `full_components`: same evidence-assisted writer and lookup, plus market-scoped rules and a fixed-claim provenance verifier. The semantic risk output is **executed once** and reused in the control arms, not entered as a hardcoded baseline. All three arm names describe components in this offline benchmark; they are not separately deployed LangGraph/HITL production systems.

The benchmark does not exercise the full revision loop, human approval, database import, pgvector ranking, throughput, live platform data, or manufacturer-approved SKU dossiers. Its curated lookup queries frequently include the product name, making retrieval easier than unseen user queries. The risk phrases are short and selected, so recall is a narrow screening result, not a regulatory compliance guarantee. A future external holdout, blinded annotation, query difficulty strata, and real database search are needed before claiming production effects.

The generated-claim metric covers the structured `claims` array only. A writer could omit a factual statement in title/body from that array; this benchmark has no independent claim-extraction coverage annotation, so it does not establish whole-draft factual consistency. Any high claim rate still needs a separate manual or independently annotated body audit before use as a marketing-quality claim.

On the first full local Qwen run (2026-09-15, dataset SHA-256 `3564214d8faafef83d112a6c7d1f0b57a751c120d8cefb23f9faf0ea33638633`, zero failed calls), the evidence-assisted Writer produced **0 directly supported claims out of 45 factual claims**, under the earlier identity-inclusive metric. A one-case claim audit showed it inferred dry-skin suitability from the product name and used a crowdsourced listing for moisturizing efficacy without direct official support. The Writer prompt was tightened to keep third-party records unverified and to emit only the exact user-supplied product-name claim when official evidence is absent. The second full run below shows this reduced unsupported **structured** claims across 20 product anchors; it does not show whole-draft or substantive grounding.

## Measured post-change local result

The second full Qwen run (`qwen2.5:14b`, 2026-09-15 16:02 UTC, same SHA-256 above) completed all 80 cases with **zero model-call failures**. The current ignored `evaluation/report.json` stores the case-level audit; the first-pass report was retained only under ignored `data/private/qwen_first_pass.json`.

| Measure | Full components | Controlled ablations |
| --- | --- | --- |
| Routing Accuracy | 20/20 (100%) | 20/20 for both; same Planner output is reused. |
| Lexical product Recall@5 | 20/20 (100%) | Single LLM has no retrieval; LLM+RAG also 20/20. Queries often include the product name. |
| Fixed claim/evidence classification | 20/20 (100%) | Only the full provenance verifier is measured; this is deterministic, not a Qwen score. |
| Substantive Grounded Claim Rate | **not measurable: 0 substantive factual claims** | Both writer ablations emitted 0 substantive factual claims. The identity-inclusive diagnostic is 20/20 with evidence and 0/20 without evidence, but it only tests a user-supplied product name. |
| Compliance Recall | 12/12 (100%) | Model-only semantic screening was 9/12 (75%) in this run. |
| Compliance false positives | 0/8 safe phrases | 0/8 for model-only screening. |

This is an in-memory, title-biased, curated component benchmark. A 100% score over 20 lookups or 12 selected risk phrases is not evidence of live-market recall, full legal compliance, manufacturer-verified claims, or deployment at million-row scale. The intended safe behavior is to **avoid unsupported product facts**, not to manufacture a high groundedness score; the live-draft audit below shows the Writer has not fully achieved that. A substantive Grounded Claim Rate requires rights-cleared, manufacturer-confirmed per-SKU evidence and an independently annotated claim/body holdout.

After this report, a separate live-draft body audit found that Qwen still wrote unsupported moisturizing/skin-type assertions in prose despite emitting only a grounded name claim, and the then-current semantic review **passed** it. An internal `PROSE_FACT_UNVERIFIED` cue screen was added to fail that exact class of draft closed; a real Qwen recheck and deterministic bounded-revision test confirmed the draft is now rejected. This post-report guard is **not** represented by the 12/12 phrase-screening score above. A blinded prose-claim coverage cohort is still required before claiming whole-draft safety.

Résumé-safe wording for this run: “基于 Qwen2.5:14B 构建 80 条分维度离线组件评测用例（每类 20 条）；在已知商品名的本地词项检索场景，Planner 路由和 Recall@5 均为 20/20；对 12 条人工标记高风险表达，规则+模型审核命中 12/12，模型单独审核命中 9/12，8 条安全表达无误报。当前尚无可验证的厂家 SKU 功效材料，故不报告实质事实 Grounded Claim Rate。” Do not use the earlier approximate 92/84/90/94 numbers without a separate, preserved historical report whose denominators support them.

The 20 routing and 20 lookup cases have 5-percentage-point score increments; the 12 risk-positive cases have 8.33-point recall increments. Consequently, 92% Routing Accuracy, 84% RAG Recall@5, and 94% Compliance Recall cannot be exact results of this particular 80-case split. They would need a separately documented historical cohort with different denominators; otherwise update the résumé to this report's actual counts.
