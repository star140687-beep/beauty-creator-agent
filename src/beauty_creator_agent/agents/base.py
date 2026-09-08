from typing import Protocol

from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.compliance import ComplianceResult
from beauty_creator_agent.schemas.content import ContentDraft
from beauty_creator_agent.schemas.planner import PlannerDecision
from beauty_creator_agent.schemas.task import TaskCreate


class ModelProvider(Protocol):
    """Model operations required by the workflow, independent of vendor."""

    async def plan(self, request: TaskCreate) -> PlannerDecision: ...

    async def write(self, state: MarketingState) -> ContentDraft: ...

    async def check(self, draft: ContentDraft) -> ComplianceResult: ...
