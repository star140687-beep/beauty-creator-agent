from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field

from beauty_creator_agent.schemas.common import ContractModel, NonEmptyStr
from beauty_creator_agent.schemas.task import TaskCreate


class ReviewRequest(ContractModel):
    action: Literal["approve", "edit", "reject"]
    feedback: str | None = None
    body: NonEmptyStr | None = None


class WorkflowEvent(ContractModel):
    event: NonEmptyStr
    task_id: NonEmptyStr
    node: NonEmptyStr
    status: NonEmptyStr
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data: dict[str, Any] = Field(default_factory=dict)


class TaskView(ContractModel):
    task_id: NonEmptyStr
    thread_id: NonEmptyStr
    status: NonEmptyStr
    request: TaskCreate
    state: dict[str, Any] = Field(default_factory=dict)
    events: list[WorkflowEvent] = Field(default_factory=list)
