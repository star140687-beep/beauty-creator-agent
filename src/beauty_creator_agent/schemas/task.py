from typing import Literal

from pydantic import Field, HttpUrl, field_validator

from beauty_creator_agent.core.prompt_safety import wrap_untrusted_document
from beauty_creator_agent.schemas.common import ContractModel, Market, NonEmptyStr, Platform


class ProductInput(ContractModel):
    """Product information supplied directly by the user."""

    brand: NonEmptyStr | None = None
    name: NonEmptyStr
    description: NonEmptyStr | None = None
    official_url: HttpUrl | None = None


class UploadedReference(ContractModel):
    """Text extracted transiently from a user-supplied reference file."""

    source_id: NonEmptyStr
    role: Literal["brief", "product_material", "existing_content"]
    media_type: NonEmptyStr
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(gt=0, le=10 * 1024 * 1024)
    content: str = Field(min_length=1, max_length=100_000)

    @field_validator("content")
    @classmethod
    def mark_uploaded_text_as_untrusted(cls, value: str) -> str:
        return wrap_untrusted_document(value)


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
    uploaded_references: list[UploadedReference] = Field(default_factory=list, max_length=3)
