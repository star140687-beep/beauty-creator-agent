from dataclasses import dataclass, field
from typing import Literal

from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.compliance import ComplianceIssue, ComplianceResult
from beauty_creator_agent.schemas.content import ContentDraft, GeneratedClaim
from beauty_creator_agent.schemas.planner import PlannerDecision
from beauty_creator_agent.schemas.task import TaskCreate


@dataclass(slots=True)
class FakeLLMProvider:
    """Deterministic provider used by tests and local development."""

    compliance_failures_before_pass: int = 0
    always_fail_compliance: bool = False
    compliance_calls: int = field(default=0, init=False)

    async def plan(self, request: TaskCreate) -> PlannerDecision:
        intent: Literal["generate", "rewrite"] = (
            "rewrite" if request.existing_content else "generate"
        )
        return PlannerDecision(
            intent=intent,
            platform=request.platform,
            needs_product_research=True,
            needs_consumer_research=intent == "generate",
            needs_content_research=True,
            needs_trend_research=False,
            needs_writer=True,
            needs_compliance=True,
            reasoning_summary="Deterministic development plan",
        )

    async def write(self, state: MarketingState) -> ContentDraft:
        request = state["request"]
        revision_count = state.get("revision_count", 0)
        suffix = "（修订版）" if state.get("current_draft") else ""
        source_ids = [item.source_id for item in state.get("evidence", []) if item.source_id]
        return ContentDraft(
            title=f"{request.product.name}体验重点{suffix}",
            body=(
                f"围绕{request.product.name}的使用场景，整理质地、搭配与适用人群。"
                f"这是第 {revision_count + 1} 版草稿，实际感受因人而异。"
            ),
            hashtags=["护肤", "理性种草"],
            claims=[
                GeneratedClaim(
                    text=f"产品名称为{request.product.name}",
                    claim_type="product_fact",
                    source_ids=source_ids,
                )
            ],
            source_ids=source_ids,
        )

    async def check(self, _draft: ContentDraft) -> ComplianceResult:
        self.compliance_calls += 1
        should_fail = self.always_fail_compliance or (
            self.compliance_calls <= self.compliance_failures_before_pass
        )
        if not should_fail:
            return ComplianceResult(status="pass")
        return ComplianceResult(
            status="fail",
            issues=[
                ComplianceIssue(
                    code="FAKE_001",
                    category="test_failure",
                    severity="medium",
                    message="Configured fake compliance failure",
                )
            ],
            revision_instructions=["Revise the draft using the configured fake feedback"],
        )
