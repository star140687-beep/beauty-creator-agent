from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

Platform = Literal["xiaohongshu", "douyin", "bilibili", "weibo"]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ContractModel(BaseModel):
    """Base model for strict contracts crossing application boundaries."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )
