from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from beauty_creator_agent.agents.base import ModelProvider
from beauty_creator_agent.agents.factory import get_model_provider
from beauty_creator_agent.graph.nodes.workflow import WorkflowNodes
from beauty_creator_agent.graph.routing import route_after_compliance
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.services.compliance import ComplianceSystem
from beauty_creator_agent.services.research import ResearchService, sample_catalog


def build_graph(
    provider: ModelProvider | None = None,
    *,
    max_revision_count: int = 2,
    enable_interrupts: bool = False,
    checkpointer: BaseCheckpointSaver[str] | None = None,
) -> CompiledStateGraph[MarketingState, None, MarketingState, MarketingState]:
    """Build the deterministic workflow skeleton with in-memory checkpoints."""
    resolved_provider = provider or get_model_provider()
    nodes = WorkflowNodes(
        resolved_provider,
        ResearchService(sample_catalog()),
        ComplianceSystem(resolved_provider),
        enable_interrupts=enable_interrupts,
    )
    graph = StateGraph(MarketingState)
    graph.add_node("normalize_request", nodes.normalize_request)
    graph.add_node("planner", nodes.planner)
    graph.add_node("research", nodes.research_node)
    graph.add_node("writer", nodes.writer)
    graph.add_node("compliance", nodes.compliance)
    graph.add_node("prepare_review", nodes.prepare_review)  # type: ignore[arg-type]
    graph.add_node("human_review", nodes.human_review)
    graph.add_node("finalize", nodes.finalize)

    graph.add_edge(START, "normalize_request")
    graph.add_edge("normalize_request", "planner")
    graph.add_edge("planner", "research")
    graph.add_edge("research", "writer")
    graph.add_edge("writer", "compliance")

    def router(state: MarketingState) -> str:
        return route_after_compliance(state, max_revision_count=max_revision_count)

    graph.add_conditional_edges(
        "compliance",
        router,
        {"writer": "writer", "human_review": "prepare_review"},
    )
    graph.add_edge("prepare_review", "human_review")

    def route_after_review(state: MarketingState) -> str:
        return "finalize" if state.get("human_action") else "end"

    graph.add_conditional_edges(
        "human_review", route_after_review, {"finalize": "finalize", "end": END}
    )
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())
