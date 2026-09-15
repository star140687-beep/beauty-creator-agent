from pydantic import Field, HttpUrl

from beauty_creator_agent.schemas.common import ContractModel, Market, NonEmptyStr, Platform


class ProductInput(ContractModel):
    """Product information supplied directly by the user."""

    brand: NonEmptyStr | None = None
    name: NonEmptyStr
    description: NonEmptyStr | None = None
    official_url: HttpUrl | None = None


class TaskCreate(ContractModel):
    """Input contract for a content workflow request."""

    product: ProductInput
    platform: Platform
    market: Market = "CN"
    objective: NonEmptyStr
    audience: NonEmptyStr | None = None
    requirements: NonEmptyStr | None = None
    existing_content: NonEmptyStr | None = None
    target_length: int = Field(default=800, ge=200, le=5000)
