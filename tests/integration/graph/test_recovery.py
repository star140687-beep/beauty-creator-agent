import pytest
from langgraph.checkpoint.memory import InMemorySaver

from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.schemas.api import ReviewRequest
from beauty_creator_agent.schemas.task import ProductInput, TaskCreate
from beauty_creator_agent.services.tasks import TaskManager


@pytest.mark.asyncio
async def test_new_manager_recovers_waiting_thread_from_checkpointer() -> None:
    checkpointer = InMemorySaver()
    first = TaskManager(FakeLLMProvider(), checkpointer)
    task = first.create(
        TaskCreate(
            product=ProductInput(name="Barrier Serum"),
            platform="xiaohongshu",
            objective="Generate content",
        )
    )
    await first.run(task.task_id)
    assert task.status == "awaiting_human_review"

    restarted = TaskManager(FakeLLMProvider(), checkpointer)
    recovered = await restarted.review(task.task_id, ReviewRequest(action="approve"))

    assert recovered.status == "completed"
    assert recovered.state["human_action"] == "approve"
