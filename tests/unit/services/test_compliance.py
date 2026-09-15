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


@pytest.mark.asyncio
async def test_unlisted_product_fact_in_body_fails_closed() -> None:
    name = "Jergens Original Scent Dry Skin Moisturizer"
    name_evidence = EvidenceItem(
        id="user_product_name",
        evidence_type="product_fact",
        source_type="user_input",
        source_id="user_product_input",
        content=f"产品名称：{name}",
        reliability="high",
    )
    draft = ContentDraft(
        title=name,
        body=f"{name} 专为干燥肌肤设计，帮助改善肌肤水分状态。",
        claims=[
            GeneratedClaim(
                text=f"产品名称为{name}",
                claim_type="product_fact",
                source_ids=["user_product_input"],
            )
        ],
    )

    result = await ComplianceSystem(FakeLLMProvider()).check(draft, [name_evidence])

    assert result.status == "fail"
    assert any(issue.code == "PROSE_FACT_UNVERIFIED" for issue in result.issues)
    assert result.claim_verifications[0].status == "supported"


@pytest.mark.asyncio
async def test_crowdsourced_listing_cannot_clear_unlisted_body_fact() -> None:
    listing = EvidenceItem(
        id="crowdsourced_listing",
        evidence_type="product_fact",
        source_type="external_search",
        source_id="obf:test",
        content="Moisturizing cream",
        reliability="medium",
    )
    draft = ContentDraft(title="Product", body="This product helps improve hydration")

    result = await ComplianceSystem(FakeLLMProvider()).check(draft, [listing])

    assert result.status == "fail"
    assert any(issue.code == "PROSE_FACT_UNVERIFIED" for issue in result.issues)


@pytest.mark.asyncio
async def test_one_official_claim_does_not_clear_a_different_body_claim() -> None:
    draft = ContentDraft(
        title="Product",
        body="Contains ceramides. Contains rocket fuel.",
        claims=[
            GeneratedClaim(
                text="Contains ceramides",
                claim_type="product_fact",
                source_ids=["source_1"],
            )
        ],
    )

    result = await ComplianceSystem(FakeLLMProvider()).check(draft, evidence())

    assert result.status == "fail"
    assert any(issue.code == "PROSE_FACT_UNVERIFIED" for issue in result.issues)


@pytest.mark.asyncio
async def test_matching_id_from_review_cannot_support_product_fact() -> None:
    draft = ContentDraft(
        title="Product",
        body="Contains ceramides",
        claims=[
            GeneratedClaim(
                text="Contains ceramides",
                claim_type="product_fact",
                source_ids=["review_1"],
            )
        ],
    )
    review = EvidenceItem(
        id="review_1",
        evidence_type="consumer_review",
        source_type="consumer_dataset",
        source_id="review_1",
        content="Contains ceramides",
        reliability="medium",
    )

    result = await ComplianceSystem(FakeLLMProvider()).check(draft, [review])

    assert result.status == "fail"
    assert result.claim_verifications[0].status == "unsupported"


@pytest.mark.asyncio
async def test_unrelated_official_text_cannot_support_claim() -> None:
    draft = ContentDraft(
        title="Product",
        body="Cures acne",
        claims=[
            GeneratedClaim(
                text="Cures acne", claim_type="product_fact", source_ids=["source_1"]
            )
        ],
    )

    result = await ComplianceSystem(FakeLLMProvider()).check(draft, evidence())

    assert result.status == "fail"
    assert result.claim_verifications[0].status == "unsupported"


@pytest.mark.asyncio
async def test_market_rules_are_scoped_and_keep_official_provenance() -> None:
    draft = ContentDraft(title="EU approved moisturizer", body="A regular moisturizer")
    system = ComplianceSystem(FakeLLMProvider())

    eu = await system.check(draft, [], market="EU")
    cn = await system.check(draft, [], market="CN")

    assert any(issue.code == "EU_APPROVAL_001" and issue.source_url for issue in eu.issues)
    assert not any(issue.code == "EU_APPROVAL_001" for issue in cn.issues)


@pytest.mark.asyncio
async def test_us_drug_claim_requires_review_but_cn_rule_does_not_apply() -> None:
    draft = ContentDraft(title="Treats eczema", body="A product")
    system = ComplianceSystem(FakeLLMProvider())

    us = await system.check(draft, [], market="US")
    cn = await system.check(draft, [], market="CN")

    assert any(issue.code == "US_DRUG_001" for issue in us.issues)
    assert not any(issue.code == "US_DRUG_001" for issue in cn.issues)
