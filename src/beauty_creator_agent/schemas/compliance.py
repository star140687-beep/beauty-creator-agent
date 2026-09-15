from datetime import date
from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from beauty_creator_agent.schemas.common import ContractModel, Market, NonEmptyStr


class ComplianceRule(ContractModel):
    """A versioned screening heuristic with explicit provenance and market scope."""

    id: NonEmptyStr
    regulatory_source_id: NonEmptyStr
    markets: list[Market] = Field(min_length=1)
    pattern: NonEmptyStr
    severity: Literal["low", "medium", "high"]
    category: NonEmptyStr
    message: NonEmptyStr
    source_kind: Literal["official", "internal_policy"]
    source_title: NonEmptyStr
    source_url: HttpUrl | None = None
    basis: NonEmptyStr
    effective_date: date | None = None

    @model_validator(mode="after")
    def require_official_source(self) -> "ComplianceRule":
        if self.source_kind == "official" and self.source_url is None:
            raise ValueError("official compliance rules require a source URL")
        return self


class ComplianceIssue(ContractModel):
    """A rule, evidence, or semantic issue found in a draft."""

    code: NonEmptyStr
    category: NonEmptyStr
    severity: Literal["low", "medium", "high"]
    message: NonEmptyStr
    claim_text: NonEmptyStr | None = None
    market: Market | None = None
    source_url: HttpUrl | None = None
    source_basis: NonEmptyStr | None = None
    regulatory_source_id: NonEmptyStr | None = None


class ClaimVerification(ContractModel):
    """Evidence support result for one generated claim."""

    claim_text: NonEmptyStr
    status: Literal["supported", "unsupported", "uncertain"]
    source_ids: list[NonEmptyStr] = Field(default_factory=list)
    explanation: NonEmptyStr


class ComplianceResult(ContractModel):
    """Typed, fail-closed result returned by the compliance system."""

    status: Literal["pass", "fail"]
    issues: list[ComplianceIssue] = Field(default_factory=list)
    claim_verifications: list[ClaimVerification] = Field(default_factory=list)
    revision_instructions: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_status_details(self) -> "ComplianceResult":
        if self.status == "pass" and self.issues:
            raise ValueError("passing compliance result cannot contain issues")
        if self.status == "fail" and not self.issues:
            raise ValueError("failing compliance result must contain at least one issue")
        if self.status == "fail" and not self.revision_instructions:
            raise ValueError("failing compliance result requires revision instructions")
        return self
