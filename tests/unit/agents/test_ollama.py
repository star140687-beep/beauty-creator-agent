import json

import httpx
import pytest
import respx

from beauty_creator_agent.agents.ollama import OllamaProvider
from beauty_creator_agent.core.errors import ExternalServiceError
from beauty_creator_agent.schemas.content import ContentDraft
from beauty_creator_agent.schemas.evidence import EvidenceItem
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
    assert request_payload["model"] == "llama3.2:3b"
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


@pytest.mark.asyncio
@respx.mock
async def test_ollama_retries_json_mode_after_schema_server_failure() -> None:
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
        side_effect=[
            httpx.Response(502, json={"error": "schema unavailable"}),
            httpx.Response(200, json={"message": {"content": decision.model_dump_json()}}),
        ]
    )

    result = await OllamaProvider().plan(task())

    assert result == decision
    assert len(route.calls) == 2
    assert json.loads(route.calls[1].request.content)["format"] == "json"


@pytest.mark.asyncio
@respx.mock
async def test_ollama_semantic_uses_small_schema_and_full_contract() -> None:
    route = respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {"risk_detected": True, "uncertain": False, "trigger": "100%有效"}
                    )
                }
            },
        )
    )

    result = await OllamaProvider().check(ContentDraft(title="100%有效", body="合成样本"))

    assert result.status == "fail"
    assert result.issues[0].code == "SEMANTIC_RISK"
    request_payload = json.loads(route.calls.last.request.content)
    assert request_payload["format"]["title"] == "SemanticScreen"
    assert "ComplianceResult" not in json.dumps(request_payload["format"])


@pytest.mark.asyncio
@respx.mock
async def test_ollama_semantic_server_failure_fails_closed() -> None:
    respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(500, json={"error": "synthetic failure"})
    )
    with pytest.raises(ExternalServiceError):
        await OllamaProvider().check(ContentDraft(title="Safe", body="合成样本"))


@pytest.mark.asyncio
@respx.mock
async def test_writer_marks_crowdsourced_records_unverified() -> None:
    draft = ContentDraft(title="Barrier Serum", body="中性介绍")
    route = respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": draft.model_dump_json()}})
    )
    evidence = [
        EvidenceItem(
            id="user_product_name",
            evidence_type="product_fact",
            source_type="user_input",
            source_id="user_product_input",
            content="产品名称：Barrier Serum",
            reliability="high",
        ),
        EvidenceItem(
            id="crowd_listing",
            evidence_type="product_fact",
            source_type="external_search",
            source_id="obf:test",
            content="Unverified listing",
            reliability="medium",
        ),
    ]

    result = await OllamaProvider().write({"request": task(), "evidence": evidence})

    assert result == draft
    payload = json.loads(route.calls.last.request.content)
    assert "第三方众包资料不能证明功效" in payload["messages"][0]["content"]
    assert '"allowed_identity_claim"' in payload["messages"][1]["content"]


@pytest.mark.asyncio
@respx.mock
async def test_writer_receives_previous_draft_for_length_expansion() -> None:
    previous = ContentDraft(title="Draft", body="Short starting body.")
    replacement = ContentDraft(title="Draft", body="Expanded replacement body.")
    route = respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(
            200, json={"message": {"content": replacement.model_dump_json()}}
        )
    )

    result = await OllamaProvider().write({"request": task(), "current_draft": previous})

    assert result == replacement
    prompt = json.loads(route.calls.last.request.content)["messages"][1]["content"]
    assert "previous_draft" in prompt
    assert previous.body in prompt
