from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report whether the API process is responsive."""
    return HealthResponse(status="ok")
