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
        planner_model: str = "llama3.2:3b",
        writer_model: str = "qwen2.5:14b",
        compliance_model: str = "llama3.2:3b",
        keep_alive: str = "15m",
        timeout_seconds: float = 180.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.planner_model = planner_model
        self.writer_model = writer_model
        self.compliance_model = compliance_model
        self.keep_alive = keep_alive
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
                        f"{prompt}\n\n严格按照以下 JSON Schema 输出：\n"
                        f"{json.dumps(schema, ensure_ascii=False)}"
                    ),
                },
            ],
            "stream": False,
            "keep_alive": self.keep_alive,
            "format": schema,
            "options": options or {"temperature": 0},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                if response.is_server_error:
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
                "你是美妆内容工作流的 Planner。只负责识别意图并选择研究、写作和合规节点；"
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
        previous_draft = state.get("current_draft")
        minimum_length = int(request.target_length * 0.6)
        prompt_data = {
            "request": request.model_dump(mode="json"),
            "evidence": evidence,
            "allowed_identity_claim": {
                "text": f"产品名称为{request.product.name}",
                "claim_type": "product_fact",
                "source_ids": ["user_product_input"],
            },
            "user_description_policy": (
                "user_product_description 可支持与原文直接一致的普通产品描述，"
                "但必须注明来自用户提供资料，不得升级为医疗、绝对化或量化功效。"
            ),
            "revision_count": state.get("revision_count", 0),
            "revision_instructions": revision,
            "target_body_characters": request.target_length,
            "minimum_body_characters": minimum_length,
            "length_feedback": state.get("length_feedback"),
            "previous_draft": (
                previous_draft.model_dump(mode="json") if previous_draft is not None else None
            ),
            "length_policy": (
                "正文长度是明确要求。使用有变化的段落、场景、步骤和克制表达达到长度；"
                "不得重复句子，也不得为了凑字数添加无证据事实。"
            ),
            "expansion_policy": (
                "若 previous_draft 不为空，必须保留其中合规且有证据的内容，"
                "在其基础上扩写，并返回完整的替换版正文，而不是只返回新增片段。"
            ),
        }
        output_token_budget = min(8192, max(1024, math.ceil(request.target_length * 1.5)))
        return await self._structured_chat(
            model=self.writer_model,
            system=(
                "你是小红书美妆内容 Writer。产品名称只能证明名称本身。"
                "用户提供的产品描述可作为未核验 brief 使用，仅支持与原文直接一致的普通描述；"
                "不得据此生成医疗、绝对化、量化功效或安全保证。第三方众包资料不能证明功效。"
                "只有官方证据可支持额外明确功效。所有事实 claim 必须引用对应 source_id。"
                "在这些边界内充分展开生活场景、内容结构、使用步骤和主观表达。"
            ),
            prompt=f"根据以下上下文生成结构化文案：\n{json.dumps(prompt_data, ensure_ascii=False)}",
            response_model=ContentDraft,
            options={"temperature": 0.3, "num_predict": output_token_budget},
        )

    async def check(self, draft: ContentDraft) -> ComplianceResult:
        screen = await self._structured_chat(
            model=self.compliance_model,
            system=(
                "你是美妆营销合规审查员。检查绝对化功效、医疗宣称、伪装体验、"
                "无来源产品事实和误导表达。只返回 risk_detected、uncertain、trigger。"
                "有疑问则 uncertain=true；无风险时 trigger 为空。"
            ),
            prompt=f"审查以下文案和 claims：\n{draft.model_dump_json(indent=2)}",
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
                    severity="high" if screen.risk_detected else "medium",
                    message=(
                        "Semantic risk detected"
                        if screen.risk_detected
                        else "Semantic review uncertain; route to human review"
                    ),
                    claim_text=screen.trigger.strip() or None,
                )
            ],
            revision_instructions=["删除或改写模型标记的高风险表达，并复核对应证据。"],
        )
