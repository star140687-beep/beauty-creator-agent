import pytest
from pydantic import ValidationError

from beauty_creator_agent.schemas.compliance import ComplianceIssue, ComplianceResult
from beauty_creator_agent.schemas.content import ContentDraft, GeneratedClaim
from beauty_creator_agent.schemas.evidence import EvidenceContext, EvidenceItem
from beauty_creator_agent.schemas.planner import PlannerDecision
from beauty_creator_agent.schemas.task import ProductInput, TaskCreate


def test_mutable_defaults_are_not_shared() -> None:
    first = EvidenceContext()
    second = EvidenceContext()

    first.warnings.append("first only")

    assert second.warnings == []


def test_evidence_requires_non_empty_content() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            id="ev_001",
            evidence_type="product_fact",
            source_type="official",
            source_id="source_001",
            content="   ",
            reliability="high",
        )


def test_content_draft_keeps_claim_provenance() -> None:
    draft = ContentDraft(
        title="A practical review",
        body="A sourced product description.",
        claims=[
            GeneratedClaim(
                text="Contains ceramides",
                claim_type="product_fact",
                source_ids=["official_001"],
            )
        ],
        source_ids=["official_001"],
    )

    assert draft.claims[0].source_ids == ["official_001"]


def test_compliance_failure_requires_issue_and_revision() -> None:
    with pytest.raises(ValidationError):
        ComplianceResult(status="fail")


def test_compliance_failure_accepts_actionable_details() -> None:
    result = ComplianceResult(
        status="fail",
        issues=[
            ComplianceIssue(
                code="ABSOLUTE_001",
                category="absolute_claim",
                severity="high",
                message="Absolute efficacy claim detected",
            )
        ],
        revision_instructions=["Remove the absolute efficacy claim"],
    )

    assert result.status == "fail"


def test_rewrite_plan_must_route_to_writer() -> None:
    with pytest.raises(ValidationError):
        PlannerDecision(
            intent="rewrite",
            platform="xiaohongshu",
            needs_product_research=False,
            needs_consumer_research=False,
            needs_content_research=True,
            needs_trend_research=False,
            needs_writer=False,
            needs_compliance=True,
            reasoning_summary="Rewrite requested",
        )


def test_task_market_defaults_to_cn_and_rejects_unknown_market() -> None:
    request = TaskCreate(
        product=ProductInput(name="A moisturizer"),
        platform="xiaohongshu",
        objective="Generate a post",
    )

    assert request.market == "CN"
    assert request.target_length == 800
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(
            {
                "product": {"name": "A moisturizer"},
                "platform": "xiaohongshu",
                "objective": "Generate a post",
                "market": "XX",
            }
        )


def test_task_rejects_an_unsafe_or_unreasonable_target_length() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(
            {
                "product": {"name": "A moisturizer"},
                "platform": "xiaohongshu",
                "objective": "Generate a post",
                "target_length": 100,
            }
        )
