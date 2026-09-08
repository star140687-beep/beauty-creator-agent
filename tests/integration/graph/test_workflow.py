from typing import cast
from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableConfig

from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.graph.builder import build_graph
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.task import ProductInput, TaskCreate


def request() -> TaskCreate:
    return TaskCreate(
        product=ProductInput(name="Barrier Serum", description="Contains ceramides"),
        platform="xiaohongshu",
        objective="Generate a natural launch post",
    )


async def run(provider: FakeLLMProvider, max_revisions: int = 2) -> MarketingState:
    graph = build_graph(provider, max_revision_count=max_revisions)
    thread_id = str(uuid4())
    config = RunnableConfig(configurable={"thread_id": thread_id})
    initial: MarketingState = {
        "request": request(),
        "task_id": "task_001",
        "thread_id": thread_id,
    }
    result = await graph.ainvoke(
        initial,
        config=config,
    )
    return cast(MarketingState, result)


@pytest.mark.asyncio
async def test_happy_path_reaches_human_review_without_revision() -> None:
    result = await run(FakeLLMProvider())

    assert result["status"] == "awaiting_human_review"
    assert result["revision_count"] == 0
    assert len(result["draft_history"]) == 1
    assert result["compliance_result"].status == "pass"


@pytest.mark.asyncio
async def test_one_compliance_failure_triggers_one_revision() -> None:
    provider = FakeLLMProvider(compliance_failures_before_pass=1)

    result = await run(provider)

    assert result["status"] == "awaiting_human_review"
    assert result["revision_count"] == 1
    assert len(result["draft_history"]) == 2
    assert provider.compliance_calls == 2
    assert result["compliance_result"].status == "pass"


@pytest.mark.asyncio
async def test_max_revision_count_prevents_infinite_loop() -> None:
    provider = FakeLLMProvider(always_fail_compliance=True)

    result = await run(provider, max_revisions=2)

    assert result["status"] == "awaiting_human_review"
    assert result["revision_count"] == 2
    assert len(result["draft_history"]) == 3
    assert provider.compliance_calls == 3
    assert result["compliance_result"].status == "fail"
