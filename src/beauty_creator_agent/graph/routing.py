from typing import Literal

from beauty_creator_agent.graph.state import MarketingState


def route_after_compliance(
    state: MarketingState,
    *,
    max_revision_count: int,
) -> Literal["writer", "human_review"]:
    """Route failures to bounded revision and all terminal drafts to review."""
    result = state["compliance_result"]
    if result.status == "fail" and state.get("revision_count", 0) < max_revision_count:
        return "writer"
    return "human_review"
