from dataclasses import dataclass, field
from typing import Any, cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from beauty_creator_agent.agents.base import ModelProvider
from beauty_creator_agent.agents.factory import get_model_provider
from beauty_creator_agent.core.config import get_settings
from beauty_creator_agent.graph.builder import build_graph
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.api import ReviewRequest, TaskView, WorkflowEvent
from beauty_creator_agent.schemas.task import TaskCreate


@dataclass
class RuntimeTask:
    task_id: str
    thread_id: str
    request: TaskCreate
    status: str = "created"
    state: MarketingState = field(default_factory=lambda: cast(MarketingState, {}))
    events: list[WorkflowEvent] = field(default_factory=list)
    graph: CompiledStateGraph[MarketingState, None, MarketingState, MarketingState] | None = None


class TaskManager:
    """Process-local task orchestration; repository persistence is the production adapter."""

    def __init__(
        self,
        provider: ModelProvider | None = None,
        checkpointer: BaseCheckpointSaver[str] | None = None,
        max_revision_count: int | None = None,
    ) -> None:
        settings = get_settings()
        self.provider = provider or get_model_provider(settings)
        self.checkpointer = checkpointer or InMemorySaver()
        self.max_revision_count = (
            settings.max_revision_count if max_revision_count is None else max_revision_count
        )
        self.tasks: dict[str, RuntimeTask] = {}

    def create(self, request: TaskCreate) -> RuntimeTask:
        task_id = str(uuid4())
        task = RuntimeTask(task_id=task_id, thread_id=task_id, request=request)
        self.tasks[task_id] = task
        self._emit(task, "task.created", "task", "created")
        return task

    async def run(self, task_id: str) -> RuntimeTask:
        task = self.require(task_id)
        task.graph = build_graph(
            self.provider,
            max_revision_count=self.max_revision_count,
            enable_interrupts=True,
            checkpointer=self.checkpointer,
        )
        config = RunnableConfig(configurable={"thread_id": task.thread_id})
        initial: MarketingState = {
            "task_id": task.task_id,
            "thread_id": task.thread_id,
            "request": task.request,
        }
        task.status = "running"
        self._emit(task, "workflow.started", "workflow", "running")
        try:
            async for update in task.graph.astream(initial, config=config, stream_mode="updates"):
                for node, node_update in update.items():
                    if node.startswith("__") or not isinstance(node_update, dict):
                        continue
                    task.state.update(cast(MarketingState, node_update))
                    phase = task.state.get("status", "running")
                    self._emit(task, "workflow.progress", node, phase)
            snapshot = await task.graph.aget_state(config)
            task.state = cast(MarketingState, snapshot.values)
            task.status = task.state.get("status", "failed")
            self._emit(
                task,
                "human_review.required"
                if task.status == "awaiting_human_review"
                else "task.completed",
                "human_review" if task.status == "awaiting_human_review" else "task",
                task.status,
            )
        except Exception as exc:
            task.status = "failed"
            task.state["errors"] = [{"code": "workflow_error", "message": str(exc), "node": None}]
            self._emit(task, "task.failed", "workflow", "failed", {"message": str(exc)})
        return task

    async def review(self, task_id: str, review: ReviewRequest) -> RuntimeTask:
        try:
            task = self.require(task_id)
        except KeyError:
            task = await self.recover(task_id)
        if task.graph is None or task.status != "awaiting_human_review":
            raise ValueError("task is not awaiting human review")
        config = RunnableConfig(configurable={"thread_id": task.thread_id})
        result = await task.graph.ainvoke(Command(resume=review.model_dump()), config=config)
        task.state = cast(MarketingState, result)
        task.status = task.state["status"]
        self._emit(task, "task.completed", "finalize", task.status)
        return task

    async def recover(self, task_id: str) -> RuntimeTask:
        """Rebuild runtime metadata from a persistent LangGraph checkpoint."""
        graph = build_graph(
            self.provider,
            max_revision_count=self.max_revision_count,
            enable_interrupts=True,
            checkpointer=self.checkpointer,
        )
        config = RunnableConfig(configurable={"thread_id": task_id})
        snapshot = await graph.aget_state(config)
        if not snapshot.values or "request" not in snapshot.values:
            raise KeyError(f"task not found: {task_id}")
        state = cast(MarketingState, snapshot.values)
        task = RuntimeTask(
            task_id=task_id,
            thread_id=task_id,
            request=state["request"],
            status=state.get("status", "failed"),
            state=state,
            graph=graph,
        )
        self.tasks[task_id] = task
        self._emit(task, "task.recovered", "checkpoint", task.status)
        return task

    def require(self, task_id: str) -> RuntimeTask:
        try:
            return self.tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"task not found: {task_id}") from exc

    def view(self, task_id: str) -> TaskView:
        task = self.require(task_id)
        serialized = {
            key: value.model_dump(mode="json") if hasattr(value, "model_dump") else value
            for key, value in task.state.items()
            if key != "request" and not key.startswith("__")
        }
        return TaskView(
            task_id=task.task_id,
            thread_id=task.thread_id,
            status=task.status,
            request=task.request,
            state=serialized,
            events=task.events,
        )

    def _emit(
        self,
        task: RuntimeTask,
        event: str,
        node: str,
        status: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        task.events.append(
            WorkflowEvent(
                event=event,
                task_id=task.task_id,
                node=node,
                status=status,
                data=data or {},
            )
        )
