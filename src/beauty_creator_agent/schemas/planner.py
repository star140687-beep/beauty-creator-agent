from typing import Literal

from pydantic import Field, model_validator

from beauty_creator_agent.schemas.common import ContractModel, NonEmptyStr, Platform


class PlannerDecision(ContractModel):
    """Structured routing decision produced by the planner."""

    intent: Literal["generate", "rewrite", "compliance_only"]
    platform: Platform
    needs_product_research: bool
    needs_consumer_research: bool
    needs_content_research: bool
    needs_trend_research: bool
    needs_writer: bool
    needs_compliance: bool
    missing_information: list[NonEmptyStr] = Field(default_factory=list)
    reasoning_summary: NonEmptyStr

    @model_validator(mode="after")
    def validate_intent_routing(self) -> "PlannerDecision":
        if self.intent == "rewrite" and not self.needs_writer:
            raise ValueError("rewrite intent requires the writer")
        if self.intent == "compliance_only" and self.needs_writer:
            raise ValueError("compliance_only intent must not route to the writer")
        if self.intent == "compliance_only" and not self.needs_compliance:
            raise ValueError("compliance_only intent requires compliance")
        return self
