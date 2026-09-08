from typing import Any, Literal, TypedDict

from beauty_creator_agent.schemas.compliance import ComplianceResult
from beauty_creator_agent.schemas.content import ContentDraft
from beauty_creator_agent.schemas.evidence import EvidenceItem
from beauty_creator_agent.schemas.planner import PlannerDecision
from beauty_creator_agent.schemas.task import TaskCreate


class StateError(TypedDict):
    """Serializable error recorded without raising across graph boundaries."""

    code: str
    message: str
    node: str | None


class MarketingState(TypedDict, total=False):
    """Shared, typed state for the future LangGraph workflow."""

    task_id: str
    thread_id: str
    request: TaskCreate
    plan: PlannerDecision
    product_facts: dict[str, Any]
    consumer_insights: list[dict[str, Any]]
    content_patterns: list[dict[str, Any]]
    trend_context: list[dict[str, Any]]
    evidence: list[EvidenceItem]
    current_draft: ContentDraft
    draft_history: list[ContentDraft]
    compliance_result: ComplianceResult
    revision_count: int
    human_action: Literal["approve", "edit", "reject"] | None
    human_feedback: str | None
    status: Literal[
        "created",
        "planning",
        "researching",
        "writing",
        "checking_compliance",
        "awaiting_human_review",
        "completed",
        "rejected",
        "failed",
    ]
    errors: list[StateError]
