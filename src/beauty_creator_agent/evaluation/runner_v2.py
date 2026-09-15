"""Labeled component evaluation with real, executed ablations.

This is not an end-to-end production or legal-certification benchmark. The
local catalog is lexical, and the generated-claim denominator depends on what
the model emits. Reports identify the model and retain failed-case counts.
"""

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from beauty_creator_agent.agents.base import ModelProvider
from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.agents.ollama import OllamaProvider
from beauty_creator_agent.schemas.content import ContentDraft, GeneratedClaim
from beauty_creator_agent.schemas.evidence import EvidenceItem
from beauty_creator_agent.schemas.task import TaskCreate
from beauty_creator_agent.services.compliance import ComplianceSystem
from beauty_creator_agent.services.research import sample_catalog
from beauty_creator_agent.tools.contracts import SearchQuery

COHORT_SIZE = 20
KINDS = ("routing", "retrieval", "grounding", "compliance")
ARM_NAMES = ("single_llm", "llm_plus_rag", "full_components")


def load_cases(
    dataset: Path, *, limit_per_kind: int = COHORT_SIZE
) -> tuple[list[dict[str, Any]], str]:
    content = dataset.read_bytes()
    rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
    counts: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    ids: set[str] = set()
    for row in rows:
        kind = row["kind"]
        if kind not in KINDS or row["id"] in ids:
            raise ValueError("dataset has an unknown kind or duplicate ID")
        ids.add(row["id"])
        if counts[kind] < limit_per_kind:
            selected.append(row)
            counts[kind] += 1
    if any(counts[kind] != limit_per_kind for kind in KINDS):
        raise ValueError("dataset must have the requested count for every kind")
    return selected, hashlib.sha256(content).hexdigest()


def _score(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _draft_evidence(case: dict[str, Any]) -> list[EvidenceItem]:
    name = case["request"]["product"]["name"]
    name_item = EvidenceItem(
        id="user_product_name",
        evidence_type="product_fact",
        source_type="user_input",
        source_id="user_product_input",
        content=f"产品名称：{name}",
        reliability="high",
    )
    gold_item = EvidenceItem.model_validate(case["evidence"])
    return [name_item] if gold_item.id == name_item.id else [name_item, gold_item]


def _claim_stats(
    draft: ContentDraft,
    evidence: list[EvidenceItem],
    compliance: ComplianceSystem,
    product_name: str,
) -> tuple[int, int, int, int, list[dict[str, Any]]]:
    factual = [
        claim
        for claim in draft.claims
        if claim.claim_type in {"product_fact", "consumer_observation"}
    ]
    if not factual:
        return 0, 0, 0, 0, []
    verification_draft = ContentDraft(title=draft.title, body=draft.body, claims=factual)
    checks = compliance.verify_claims(verification_draft, evidence)
    identity_text = f"产品名称为{product_name}"
    substantive = [
        (claim, check)
        for claim, check in zip(factual, checks, strict=True)
        if claim.text != identity_text
    ]
    audit = [
        {
            "text": claim.text,
            "source_ids": claim.source_ids,
            "status": check.status,
        }
        for claim, check in zip(factual, checks, strict=True)
    ]
    return (
        sum(item.status == "supported" for item in checks),
        len(checks),
        sum(check.status == "supported" for _, check in substantive),
        len(substantive),
        audit,
    )


async def run(
    dataset: Path,
    provider: ModelProvider,
    *,
    provider_name: str,
    model_name: str | None = None,
    limit_per_kind: int = COHORT_SIZE,
    progress: bool = False,
) -> dict[str, Any]:
    cases, dataset_hash = load_cases(dataset, limit_per_kind=limit_per_kind)
    catalog = sample_catalog()
    compliance = ComplianceSystem(provider)
    catalog_ids = {row["source_id"] for row in catalog.products}
    for case in cases:
        if case["kind"] == "retrieval" and case["expected_source_id"] not in catalog_ids:
            raise ValueError(f"gold source ID missing from catalog: {case['id']}")

    arms: dict[str, dict[str, int]] = {
        name: dict(
            routing_correct=0,
            retrieval_hits=0,
            fixed_claim_correct=0,
            supported_generated_claims=0,
            generated_factual_claims=0,
            supported_substantive_claims=0,
            generated_substantive_claims=0,
            drafts_with_factual_claims=0,
            drafts_completed=0,
            compliance_tp=0,
            compliance_fp=0,
            compliance_tn=0,
            compliance_fn=0,
            failed_calls=0,
        )
        for name in ARM_NAMES
    }
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, 1):
        kind = case["kind"]
        row: dict[str, Any] = {"id": case["id"], "kind": kind}
        if progress:
            print(f"[{index}/{len(cases)}] {case['id']}", flush=True)

        if kind == "routing":
            try:
                plan = await provider.plan(TaskCreate.model_validate(case["request"]))
                correct = plan.intent == case["expected_intent"]
                row["predicted_intent"] = plan.intent
                for arm in arms.values():
                    arm["routing_correct"] += correct
            except Exception as exc:  # model failures remain in the denominator
                row["error_type"] = type(exc).__name__
                for arm in arms.values():
                    arm["failed_calls"] += 1

        elif kind == "retrieval":
            result = catalog.search_product_knowledge(SearchQuery(query=case["query"], limit=5))
            hit = case["expected_source_id"] in result.source_ids
            row["retrieval_hit"] = hit
            row["retrieved_source_ids"] = result.source_ids
            arms["llm_plus_rag"]["retrieval_hits"] += hit
            arms["full_components"]["retrieval_hits"] += hit

        elif kind == "grounding":
            gold_evidence = [EvidenceItem.model_validate(case["evidence"])]
            gold_claim = GeneratedClaim(
                text=case["claim_text"],
                claim_type="product_fact",
                source_ids=[gold_evidence[0].source_id] if gold_evidence[0].source_id else [],
            )
            gold_draft = ContentDraft(
                title="待核查产品事实", body="固定事实核验样本", claims=[gold_claim]
            )
            verification = compliance.verify_claims(gold_draft, gold_evidence)[0]
            arms["full_components"]["fixed_claim_correct"] += (
                verification.status == "supported"
            ) == case["expected_supported"]
            row["full_components_fixed_supported"] = verification.status == "supported"

            request = TaskCreate.model_validate(case["request"])
            rag_evidence = _draft_evidence(case)
            for name, evidence in (("single_llm", []), ("llm_plus_rag", rag_evidence)):
                try:
                    draft = await provider.write(
                        {"request": request, "evidence": evidence, "revision_count": 0}
                    )
                    supported, factual, substantive_supported, substantive_count, audit = (
                        _claim_stats(draft, evidence, compliance, request.product.name)
                    )
                    row[f"{name}_supported_claims"] = supported
                    row[f"{name}_factual_claims"] = factual
                    row[f"{name}_substantive_supported_claims"] = substantive_supported
                    row[f"{name}_substantive_claims"] = substantive_count
                    row[f"{name}_claim_audit"] = audit
                    for target in (name, "full_components") if name == "llm_plus_rag" else (name,):
                        arm = arms[target]
                        arm["supported_generated_claims"] += supported
                        arm["generated_factual_claims"] += factual
                        arm["supported_substantive_claims"] += substantive_supported
                        arm["generated_substantive_claims"] += substantive_count
                        arm["drafts_with_factual_claims"] += factual > 0
                        arm["drafts_completed"] += 1
                except Exception as exc:
                    row[f"{name}_error_type"] = type(exc).__name__
                    for target in (name, "full_components") if name == "llm_plus_rag" else (name,):
                        arms[target]["failed_calls"] += 1

        else:
            draft = ContentDraft(title=case["title"], body=case["body"])
            rule_flag = bool(compliance.rule_issues(draft, case["market"]))
            semantic_flag = False
            semantic_failed = False
            try:
                semantic = await provider.check(draft)
                semantic_flag = semantic.status == "fail"
            except Exception as exc:
                semantic_failed = True
                row["semantic_error_type"] = type(exc).__name__
                for arm in arms.values():
                    arm["failed_calls"] += 1
            row["rule_flag"] = rule_flag
            row["semantic_flag"] = semantic_flag if not semantic_failed else None
            for name, arm in arms.items():
                # Shared semantic output is reused in the ablation, not fabricated.
                predicted = semantic_flag or (name == "full_components" and rule_flag)
                row[f"{name}_risk_flag"] = predicted
                if case["expected_risk"]:
                    arm["compliance_tp" if predicted else "compliance_fn"] += 1
                else:
                    arm["compliance_fp" if predicted else "compliance_tn"] += 1

        results.append(row)

    risky_count = sum(case["expected_risk"] for case in cases if case["kind"] == "compliance")
    benign_count = limit_per_kind - risky_count
    summaries = []
    for name, arm in arms.items():
        summaries.append(
            {
                "name": name,
                "routing_accuracy": _score(arm["routing_correct"], limit_per_kind),
                "rag_recall_at_5": _score(arm["retrieval_hits"], limit_per_kind),
                "fixed_claim_verification_accuracy": (
                    _score(arm["fixed_claim_correct"], limit_per_kind)
                    if name == "full_components"
                    else None
                ),
                "grounded_claim_rate": _score(
                    arm["supported_substantive_claims"], arm["generated_substantive_claims"]
                ),
                "identity_inclusive_grounded_rate": _score(
                    arm["supported_generated_claims"], arm["generated_factual_claims"]
                ),
                "compliance_recall": _score(arm["compliance_tp"], risky_count),
                "compliance_precision": _score(
                    arm["compliance_tp"], arm["compliance_tp"] + arm["compliance_fp"]
                ),
                "compliance_specificity": _score(arm["compliance_tn"], benign_count),
                "counts": arm,
            }
        )
    return {
        "protocol": "component_ablation_v2",
        "dataset": str(dataset),
        "dataset_sha256": dataset_hash,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "provider": provider_name,
        "model": model_name,
        "case_count": len(cases),
        "full_80_case_run": len(cases) == 80,
        "measurement_complete": (
            len(cases) == 80
            and provider_name == "ollama"
            and all(arm["failed_calls"] == 0 for arm in arms.values())
        ),
        "risk_positive_cases": risky_count,
        "risk_negative_cases": benign_count,
        "catalog": "local sample + 163 crowdsourced OBF records; lexical overlap, not pgvector",
        "arms": summaries,
        "cases": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the labeled v2 component benchmark")
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/datasets/v2.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/report.json"))
    parser.add_argument("--provider", choices=("fake", "ollama"), default="ollama")
    parser.add_argument("--model", default="qwen2.5:14b")
    parser.add_argument("--limit-per-kind", type=int, default=COHORT_SIZE)
    args = parser.parse_args()
    if not 1 <= args.limit_per_kind <= COHORT_SIZE:
        parser.error("--limit-per-kind must be 1..20")
    provider: ModelProvider = (
        OllamaProvider(
            planner_model=args.model, writer_model=args.model, compliance_model=args.model
        )
        if args.provider == "ollama"
        else FakeLLMProvider()
    )
    report = asyncio.run(
        run(
            args.dataset,
            provider,
            provider_name="ollama" if args.provider == "ollama" else "deterministic_test_double",
            model_name=args.model if args.provider == "ollama" else None,
            limit_per_kind=args.limit_per_kind,
            progress=True,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["arms"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
