import json
from pathlib import Path

import pytest

from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.core.errors import ExternalServiceError
from beauty_creator_agent.evaluation.case_seeds import build_cases
from beauty_creator_agent.evaluation.runner_v2 import load_cases, run
from beauty_creator_agent.schemas.compliance import ComplianceResult
from beauty_creator_agent.schemas.content import ContentDraft

DATASET = Path("evaluation/datasets/v2.jsonl")


def test_labeled_dataset_has_80_independent_scored_cases() -> None:
    cases, digest = load_cases(DATASET)
    assert len(cases) == 80
    assert len({case["id"] for case in cases}) == 80
    assert len(digest) == 64
    assert {
        kind: sum(case["kind"] == kind for case in cases)
        for kind in ("routing", "retrieval", "grounding", "compliance")
    } == {kind: 20 for kind in ("routing", "retrieval", "grounding", "compliance")}
    assert sum(case["expected_risk"] for case in cases if case["kind"] == "compliance") == 12
    assert sum(case["expected_supported"] for case in cases if case["kind"] == "grounding") == 10
    assert cases == build_cases()


@pytest.mark.asyncio
async def test_ablation_is_executed_and_fake_results_are_identified() -> None:
    report = await run(DATASET, FakeLLMProvider(), provider_name="deterministic_test_double")
    arms = {arm["name"]: arm for arm in report["arms"]}

    assert report["case_count"] == 80
    assert report["provider"] == "deterministic_test_double"
    assert report["measurement_complete"] is False
    assert arms["single_llm"]["counts"]["drafts_completed"] == 20
    assert arms["llm_plus_rag"]["counts"]["drafts_completed"] == 20
    assert arms["single_llm"]["identity_inclusive_grounded_rate"] == 0
    assert arms["llm_plus_rag"]["identity_inclusive_grounded_rate"] == 1
    assert arms["llm_plus_rag"]["grounded_claim_rate"] is None
    assert arms["llm_plus_rag"]["counts"]["generated_substantive_claims"] == 0
    assert arms["full_components"]["counts"]["compliance_tp"] == 9
    assert arms["full_components"]["fixed_claim_verification_accuracy"] == 1
    assert arms["single_llm"]["fixed_claim_verification_accuracy"] is None


class FailingSemanticProvider(FakeLLMProvider):
    async def check(self, _draft: ContentDraft) -> ComplianceResult:
        raise ExternalServiceError("injected test failure")


@pytest.mark.asyncio
async def test_model_failure_stays_in_denominator() -> None:
    report = await run(
        DATASET,
        FailingSemanticProvider(),
        provider_name="deterministic_test_double",
        limit_per_kind=2,
    )
    arms = {arm["name"]: arm for arm in report["arms"]}
    assert report["case_count"] == 8
    assert report["full_80_case_run"] is False
    assert report["measurement_complete"] is False
    assert arms["single_llm"]["counts"]["failed_calls"] == 2
    assert arms["single_llm"]["compliance_recall"] == 0
    assert arms["full_components"]["compliance_recall"] == 1


@pytest.mark.asyncio
async def test_missing_gold_product_is_rejected(tmp_path: Path) -> None:
    cases = build_cases()[:4]
    cases[1]["expected_source_id"] = "openbeautyfacts:missing"
    dataset = tmp_path / "bad.jsonl"
    dataset.write_text("".join(json.dumps(case) + "\n" for case in cases), encoding="utf-8")
    with pytest.raises(ValueError, match="gold source ID missing"):
        await run(
            dataset,
            FakeLLMProvider(),
            provider_name="deterministic_test_double",
            limit_per_kind=1,
        )
