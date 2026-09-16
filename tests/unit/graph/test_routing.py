from typing import cast

from beauty_creator_agent.graph.routing import route_after_compliance
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.compliance import ComplianceIssue, ComplianceResult


def test_semantic_uncertainty_routes_directly_to_human_review() -> None:
    state = cast(
        MarketingState,
        {
            "revision_count": 0,
            "compliance_result": ComplianceResult(
                status="fail",
                issues=[
                    ComplianceIssue(
                        code="SEMANTIC_UNCERTAIN",
                        category="semantic_review",
                        severity="medium",
                        message="Needs human review",
                    )
                ],
                revision_instructions=["Review manually"],
            ),
        },
    )

    assert route_after_compliance(state, max_revision_count=1) == "human_review"


def test_actionable_compliance_failure_gets_one_revision() -> None:
    state = cast(
        MarketingState,
        {
            "revision_count": 0,
            "compliance_result": ComplianceResult(
                status="fail",
                issues=[
                    ComplianceIssue(
                        code="ABSOLUTE_001",
                        category="absolute_claim",
                        severity="high",
                        message="Absolute claim",
                    )
                ],
                revision_instructions=["Remove the claim"],
            ),
        },
    )

    assert route_after_compliance(state, max_revision_count=1) == "writer"
