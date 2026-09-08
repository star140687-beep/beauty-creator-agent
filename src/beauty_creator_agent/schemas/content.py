from typing import Literal

from pydantic import Field

from beauty_creator_agent.schemas.common import ContractModel, NonEmptyStr


class GeneratedClaim(ContractModel):
    """A discrete claim extracted from or emitted with generated content."""

    text: NonEmptyStr
    claim_type: Literal[
        "product_fact",
        "consumer_observation",
        "subjective_expression",
        "marketing_expression",
    ]
    source_ids: list[NonEmptyStr] = Field(default_factory=list)


class ContentDraft(ContractModel):
    """Platform content plus claims required for compliance verification."""

    title: NonEmptyStr
    body: NonEmptyStr
    hashtags: list[NonEmptyStr] = Field(default_factory=list)
    claims: list[GeneratedClaim] = Field(default_factory=list)
    source_ids: list[NonEmptyStr] = Field(default_factory=list)
    warnings: list[NonEmptyStr] = Field(default_factory=list)
