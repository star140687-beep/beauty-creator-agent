from typing import Any

from pydantic import Field

from beauty_creator_agent.schemas.common import ContractModel, NonEmptyStr, Platform


class SearchQuery(ContractModel):
    query: NonEmptyStr
    limit: int = Field(default=5, ge=1, le=50)


class ContentSearchQuery(SearchQuery):
    platform: Platform


class ReviewStatisticsQuery(ContractModel):
    product_name: NonEmptyStr
    skin_type: NonEmptyStr | None = None


class ToolResult(ContractModel):
    ok: bool
    data: Any | None = None
    source_ids: list[NonEmptyStr] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
