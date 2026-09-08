import json
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from beauty_creator_agent.core.errors import ExternalServiceError
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.compliance import ComplianceResult
from beauty_creator_agent.schemas.content import ContentDraft
from beauty_creator_agent.schemas.planner import PlannerDecision
from beauty_creator_agent.schemas.task import TaskCreate

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class OllamaProvider:
    """Local Ollama provider using schema-constrained structured outputs."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        planner_model: str = "qwen2.5:14b",
        writer_model: str = "qwen2.5:14b",
        compliance_model: str = "qwen2.5:14b",
        timeout_seconds: float = 180.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.planner_model = planner_model
        self.writer_model = writer_model
        self.compliance_model = compliance_model
        self.timeout_seconds = timeout_seconds

    async def _structured_chat(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        schema = response_model.model_json_schema()
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\n严格按以下 JSON Schema 输出：\n"
                        f"{json.dumps(schema, ensure_ascii=False)}"
                    ),
                },
            ],
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                content = response.json()["message"]["content"]
            return response_model.model_validate_json(content)
        except (httpx.HTTPError, KeyError, TypeError, ValidationError, json.JSONDecodeError) as exc:
            raise ExternalServiceError(f"Ollama structured output failed: {exc}") from exc

    async def plan(self, request: TaskCreate) -> PlannerDecision:
        return await self._structured_chat(
            model=self.planner_model,
            system=(
                "你是美妆内容工作流的 Planner。只负责识别意图与选择研究、写作、合规节点；"
                "不要撰写文案，不要虚构事实。"
            ),
            prompt=f"分析以下任务并给出结构化路由：\n{request.model_dump_json(indent=2)}",
            response_model=PlannerDecision,
        )

    async def write(self, state: MarketingState) -> ContentDraft:
        request = state["request"]
        evidence = [item.model_dump(mode="json") for item in state.get("evidence", [])]
        compliance = state.get("compliance_result")
        revision = compliance.revision_instructions if compliance else []
        prompt_data = {
            "request": request.model_dump(mode="json"),
            "evidence": evidence,
            "revision_count": state.get("revision_count", 0),
            "revision_instructions": revision,
        }
        return await self._structured_chat(
            model=self.writer_model,
            system=(
                "你是小红书美妆内容 Writer。只能把 evidence 中的 product_fact 当作产品事实；"
                "不得伪造亲身体验，不得把品类洞察冒充当前产品反馈。事实 claim 必须绑定 source_ids。"
            ),
            prompt=f"根据以下可信上下文生成文案：\n{json.dumps(prompt_data, ensure_ascii=False)}",
            response_model=ContentDraft,
        )

    async def check(self, draft: ContentDraft) -> ComplianceResult:
        return await self._structured_chat(
            model=self.compliance_model,
            system=(
                "你是美妆营销合规审查员。检查绝对化功效、医疗宣称、伪装体验、"
                "无来源产品事实和误导表达。无法确认时必须 fail closed。"
            ),
            prompt=f"审查以下文案与 claims：\n{draft.model_dump_json(indent=2)}",
            response_model=ComplianceResult,
        )
