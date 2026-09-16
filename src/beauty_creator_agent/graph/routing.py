from typing import Literal

from beauty_creator_agent.graph.state import MarketingState


def route_after_compliance(
    state: MarketingState,
    *,
    max_revision_count: int,
) -> Literal["writer", "human_review"]:
    """Route failures to bounded revision and all terminal drafts to review."""
    result = state["compliance_result"]
    non_revisable_codes = {"SEMANTIC_UNCERTAIN", "SEMANTIC_REVIEW_ERROR"}
    actionable_failure = any(issue.code not in non_revisable_codes for issue in result.issues)
    if (
        result.status == "fail"
        and actionable_failure
        and state.get("revision_count", 0) < max_revision_count
    ):
        return "writer"
    return "human_review"
