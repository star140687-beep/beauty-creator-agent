from typing import get_type_hints

from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.task import ProductInput, TaskCreate


def test_marketing_state_accepts_typed_partial_state() -> None:
    state: MarketingState = {
        "task_id": "task_001",
        "thread_id": "thread_001",
        "request": TaskCreate(
            product=ProductInput(name="Barrier Serum"),
            platform="xiaohongshu",
            objective="Generate content",
        ),
        "revision_count": 0,
        "status": "created",
        "errors": [],
    }

    assert state["request"].product.name == "Barrier Serum"
    assert get_type_hints(MarketingState)["revision_count"] is int
