import json
import math
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from beauty_creator_agent.core.errors import ExternalServiceError
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.compliance import ComplianceIssue, ComplianceResult
from beauty_creator_agent.schemas.content import ContentDraft
from beauty_creator_agent.schemas.planner import PlannerDecision
from beauty_creator_agent.schemas.task import TaskCreate

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class SemanticScreen(BaseModel):
    """Small model-facing schema; the application still returns its full contract."""

    risk_detected: bool
    uncertain: bool
    trigger: str


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
        options: dict[str, Any] | None = None,
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
            "options": options or {"temperature": 0},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                if response.is_server_error:
                    # Some Ollama model builds reject complex JSON Schema, while
                    # still supporting JSON mode. Keep Pydantic validation below
                    # as the application-level contract enforcement.
                    fallback_payload = {**payload, "format": "json"}
                    response = await client.post(
                        f"{self.base_url}/api/chat", json=fallback_payload
                    )
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
            "allowed_identity_claim": {
                "text": f"产品名称为{request.product.name}",
                "claim_type": "product_fact",
                "source_ids": ["user_product_input"],
            },
            "revision_count": state.get("revision_count", 0),
            "revision_instructions": revision,
            "target_body_characters": request.target_length,
            "minimum_body_characters": int(request.target_length * 0.7),
            "length_feedback": state.get("length_feedback"),
        }
        output_token_budget = min(8192, max(1024, math.ceil(request.target_length * 1.5)))
        return await self._structured_chat(
            model=self.writer_model,
            system=(
                "你是小红书美妆内容 Writer。user_product_name 只能证明输入的产品名称；"
                "external_search 是未核实的第三方/众包信息，"
                "不能证明功效、成分、适用肤质或使用结果。"
                "只有 source_type=official 且原文直接支持的具体事实才可写成其他 product_fact。"
                "不能由产品名称推测功效，不能伪造亲身体验，也不能把品类洞察冒充该产品反馈。"
                "当没有官方证据时，正文只写中性、非事实性介绍；claims 只放提供的"
                " allowed_identity_claim，text 和 source_ids 都要逐字一致，不要加额外事实 claim。"
            ),
            prompt=f"根据以下可信上下文生成文案：\n{json.dumps(prompt_data, ensure_ascii=False)}",
            response_model=ContentDraft,
            options={"temperature": 0.2, "num_predict": output_token_budget},
        )

    async def check(self, draft: ContentDraft) -> ComplianceResult:
        screen = await self._structured_chat(
            model=self.compliance_model,
            system=(
                "你是美妆营销合规审查员。检查绝对化功效、医疗宣称、伪装体验、"
                "无来源产品事实和误导表达。只返回 risk_detected、uncertain、trigger。"
                "有疑问则 uncertain=true；无风险时 trigger 为空。"
            ),
            prompt=f"审查以下文案与 claims：\n{draft.model_dump_json(indent=2)}",
            response_model=SemanticScreen,
        )
        if not screen.risk_detected and not screen.uncertain:
            return ComplianceResult(status="pass")
        return ComplianceResult(
            status="fail",
            issues=[
                ComplianceIssue(
                    code="SEMANTIC_RISK" if screen.risk_detected else "SEMANTIC_UNCERTAIN",
                    category="semantic_review",
                    severity="high",
                    message=(
                        "Semantic risk detected"
                        if screen.risk_detected
                        else "Semantic review uncertain"
                    ),
                    claim_text=screen.trigger.strip() or None,
                )
            ],
            revision_instructions=["删除或改写模型标记的高风险表达，并复核对应证据"],
        )
