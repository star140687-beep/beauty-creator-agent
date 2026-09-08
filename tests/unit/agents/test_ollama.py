import json

import httpx
import pytest
import respx

from beauty_creator_agent.agents.ollama import OllamaProvider
from beauty_creator_agent.core.errors import ExternalServiceError
from beauty_creator_agent.schemas.planner import PlannerDecision
from beauty_creator_agent.schemas.task import ProductInput, TaskCreate


def task() -> TaskCreate:
    return TaskCreate(
        product=ProductInput(name="Barrier Serum"),
        platform="xiaohongshu",
        objective="Generate content",
    )


@pytest.mark.asyncio
@respx.mock
async def test_ollama_planner_uses_schema_constrained_output() -> None:
    decision = PlannerDecision(
        intent="generate",
        platform="xiaohongshu",
        needs_product_research=True,
        needs_consumer_research=True,
        needs_content_research=True,
        needs_trend_research=False,
        needs_writer=True,
        needs_compliance=True,
        reasoning_summary="Generate workflow",
    )
    route = respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": decision.model_dump_json()}},
        )
    )

    result = await OllamaProvider().plan(task())

    assert result == decision
    request_payload = json.loads(route.calls.last.request.content)
    assert request_payload["model"] == "qwen2.5:14b"
    assert request_payload["stream"] is False
    assert request_payload["format"]["title"] == "PlannerDecision"


@pytest.mark.asyncio
@respx.mock
async def test_ollama_invalid_output_fails_closed() -> None:
    respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": "not-json"}})
    )

    with pytest.raises(ExternalServiceError):
        await OllamaProvider().plan(task())
