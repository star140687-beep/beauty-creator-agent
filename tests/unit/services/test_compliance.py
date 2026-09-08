import pytest

from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.schemas.content import ContentDraft, GeneratedClaim
from beauty_creator_agent.schemas.evidence import EvidenceItem
from beauty_creator_agent.services.compliance import ComplianceSystem


def evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            id="ev_1",
            evidence_type="product_fact",
            source_type="official",
            source_id="source_1",
            content="Contains ceramides",
            reliability="high",
        )
    ]


@pytest.mark.asyncio
async def test_absolute_and_medical_claims_always_fail() -> None:
    draft = ContentDraft(title="100%有效", body="彻底治愈痘痘", hashtags=[])

    result = await ComplianceSystem(FakeLLMProvider()).check(draft, evidence())

    assert result.status == "fail"
    assert {issue.code for issue in result.issues} >= {"ABSOLUTE_001", "MEDICAL_001"}


@pytest.mark.asyncio
async def test_unsupported_product_claim_fails() -> None:
    draft = ContentDraft(
        title="Product",
        body="Unverified claim",
        claims=[GeneratedClaim(text="Cures acne", claim_type="product_fact")],
    )

    result = await ComplianceSystem(FakeLLMProvider()).check(draft, evidence())

    assert result.status == "fail"
    assert any(issue.code == "CLAIM_UNSUPPORTED" for issue in result.issues)


@pytest.mark.asyncio
async def test_supported_safe_claim_passes() -> None:
    draft = ContentDraft(
        title="Product",
        body="Contains ceramides",
        claims=[
            GeneratedClaim(
                text="Contains ceramides",
                claim_type="product_fact",
                source_ids=["source_1"],
            )
        ],
    )

    result = await ComplianceSystem(FakeLLMProvider()).check(draft, evidence())

    assert result.status == "pass"
