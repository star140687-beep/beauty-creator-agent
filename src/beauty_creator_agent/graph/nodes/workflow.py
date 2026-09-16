from typing import Any

from langgraph.types import interrupt

from beauty_creator_agent.agents.base import ModelProvider
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.task import TaskCreate
from beauty_creator_agent.services.compliance import ComplianceSystem
from beauty_creator_agent.services.research import ResearchService


class WorkflowNodes:
    """Phase-3 nodes with deterministic research and model behavior."""

    def __init__(
        self,
        provider: ModelProvider,
        research: ResearchService,
        compliance: ComplianceSystem,
        *,
        enable_interrupts: bool = False,
    ) -> None:
        self.provider = provider
        self.research = research
        self.compliance_system = compliance
        self.enable_interrupts = enable_interrupts

    async def normalize_request(self, state: MarketingState) -> dict[str, Any]:
        request = state["request"]
        if not isinstance(request, TaskCreate):
            request = TaskCreate.model_validate(request)
        return {
            "request": request,
            "revision_count": state.get("revision_count", 0),
            "draft_history": state.get("draft_history", []),
            "errors": state.get("errors", []),
            "status": "planning",
        }

    async def planner(self, state: MarketingState) -> dict[str, Any]:
        return {"plan": await self.provider.plan(state["request"]), "status": "researching"}

    async def research_node(self, state: MarketingState) -> dict[str, Any]:
        evidence = await self.research.research(state)
        return {"evidence": evidence, "status": "writing"}

    async def writer(self, state: MarketingState) -> dict[str, Any]:
        is_revision = "current_draft" in state
        revision_count = state.get("revision_count", 0) + (1 if is_revision else 0)
        writer_state = dict(state)
        writer_state["revision_count"] = revision_count
        draft = await self.provider.write(writer_state)  # type: ignore[arg-type]
        minimum_length = int(state["request"].target_length * 0.6)
        length_retry_count = 0
        if not is_revision and len(draft.body.strip()) < minimum_length:
            length_retry_count = 1
            writer_state["length_retry_count"] = length_retry_count
            writer_state["current_draft"] = draft
            writer_state["length_feedback"] = (
                f"The previous body has {len(draft.body.strip())} characters. "
                f"Expand it to at least {minimum_length} characters "
                "without adding unsupported facts."
            )
            draft = await self.provider.write(writer_state)  # type: ignore[arg-type]
        if len(draft.body.strip()) < minimum_length:
            draft = draft.model_copy(
                update={
                    "warnings": [
                        *draft.warnings,
                        "未达到目标长度：模型扩写一次后，正文仍低于设定的最低长度。",
                    ]
                }
            )
        history = [*state.get("draft_history", []), draft]
        return {
            "current_draft": draft,
            "draft_history": history,
            "revision_count": revision_count,
            "length_retry_count": length_retry_count,
            "status": "checking_compliance",
        }

    async def compliance(self, state: MarketingState) -> dict[str, Any]:
        result = await self.compliance_system.check(
            state["current_draft"], state.get("evidence", []), market=state["request"].market
        )
        return {"compliance_result": result}

    async def prepare_review(self, _state: MarketingState) -> dict[str, Any]:
        return {"status": "awaiting_human_review"}

    async def human_review(self, state: MarketingState) -> dict[str, Any]:
        if not self.enable_interrupts:
            return {}
        response = interrupt(
            {
                "draft": state["current_draft"].model_dump(mode="json"),
                "compliance": state["compliance_result"].model_dump(mode="json"),
                "allowed_actions": ["approve", "edit", "reject"],
            }
        )
        action = response.get("action")
        updates: dict[str, Any] = {
            "human_action": action,
            "human_feedback": response.get("feedback"),
        }
        if action == "edit" and response.get("body"):
            updates["current_draft"] = state["current_draft"].model_copy(
                update={"body": response["body"]}
            )
        return updates

    async def finalize(self, state: MarketingState) -> dict[str, Any]:
        status = "rejected" if state.get("human_action") == "reject" else "completed"
        return {"status": status}
