from typing import Any, Literal

from pydantic import Field

from beauty_creator_agent.schemas.common import ContractModel, NonEmptyStr


class EvidenceItem(ContractModel):
    """A traceable piece of information available to downstream agents."""

    id: NonEmptyStr
    evidence_type: Literal[
        "product_fact",
        "consumer_review",
        "consumer_insight",
        "content_pattern",
        "trend",
    ]
    source_type: Literal[
        "user_input",
        "official",
        "consumer_dataset",
        "content_dataset",
        "external_search",
    ]
    source_id: NonEmptyStr | None = None
    content: NonEmptyStr
    reliability: Literal["high", "medium", "low"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceContext(ContractModel):
    """Evidence bundle handed from research to writing and compliance."""

    items: list[EvidenceItem] = Field(default_factory=list)
    missing_information: list[NonEmptyStr] = Field(default_factory=list)
    warnings: list[NonEmptyStr] = Field(default_factory=list)
