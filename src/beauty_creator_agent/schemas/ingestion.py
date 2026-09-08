from pydantic import Field

from beauty_creator_agent.schemas.common import ContractModel, NonEmptyStr, Platform


class NormalizedProduct(ContractModel):
    source_id: NonEmptyStr
    brand: NonEmptyStr
    name: NonEmptyStr
    category: NonEmptyStr
    description: NonEmptyStr
    ingredients: list[NonEmptyStr] = Field(default_factory=list)
    skin_types: list[NonEmptyStr] = Field(default_factory=list)
    claims: list[NonEmptyStr] = Field(default_factory=list)
    official_url: str | None = None
    source: NonEmptyStr


class NormalizedReview(ContractModel):
    source_id: NonEmptyStr
    brand: NonEmptyStr
    product_name: NonEmptyStr
    category: NonEmptyStr
    skin_type: NonEmptyStr | None = None
    rating: float = Field(ge=1, le=5)
    review_text: NonEmptyStr
    recommended: bool | None = None
    source: NonEmptyStr


class NormalizedContent(ContractModel):
    source_id: NonEmptyStr
    platform: Platform
    category: NonEmptyStr
    title: NonEmptyStr
    body: NonEmptyStr
    hashtags: list[NonEmptyStr] = Field(default_factory=list)
    content_pattern: NonEmptyStr
    tone: NonEmptyStr
    source: NonEmptyStr
