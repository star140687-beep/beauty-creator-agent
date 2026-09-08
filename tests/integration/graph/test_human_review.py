from typing import cast
from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.graph.builder import build_graph
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.task import ProductInput, TaskCreate


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "expected"),
    [("approve", "completed"), ("edit", "completed"), ("reject", "rejected")],
)
async def test_interrupt_resume_human_actions(action: str, expected: str) -> None:
    graph = build_graph(FakeLLMProvider(), enable_interrupts=True)
    thread_id = str(uuid4())
    config = RunnableConfig(configurable={"thread_id": thread_id})
    initial: MarketingState = {
        "task_id": "task_hitl",
        "thread_id": thread_id,
        "request": TaskCreate(
            product=ProductInput(name="Barrier Serum"),
            platform="xiaohongshu",
            objective="Generate content",
        ),
    }

    paused = await graph.ainvoke(initial, config=config)
    assert paused["status"] == "awaiting_human_review"
    assert paused.get("__interrupt__")

    payload = {"action": action, "feedback": "reviewed"}
    if action == "edit":
        payload["body"] = "Human edited body"
    completed = cast(MarketingState, await graph.ainvoke(Command(resume=payload), config=config))

    assert completed["status"] == expected
    assert completed["human_action"] == action
    if action == "edit":
        assert completed["current_draft"].body == "Human edited body"
