import asyncio
import json
from collections.abc import AsyncIterator
from typing import cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from beauty_creator_agent.schemas.api import ReviewRequest, TaskView
from beauty_creator_agent.schemas.task import TaskCreate
from beauty_creator_agent.services.tasks import TaskManager

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


def manager(request: Request) -> TaskManager:
    return cast(TaskManager, request.app.state.task_manager)


@router.post("", response_model=TaskView, status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    payload: TaskCreate, request: Request, background_tasks: BackgroundTasks
) -> TaskView:
    task_manager = manager(request)
    task = task_manager.create(payload)
    background_tasks.add_task(task_manager.run, task.task_id)
    return task_manager.view(task.task_id)


@router.get("/{task_id}", response_model=TaskView)
async def get_task(task_id: str, request: Request) -> TaskView:
    try:
        return manager(request).view(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{task_id}/history")
async def get_history(task_id: str, request: Request) -> list[dict[str, object]]:
    try:
        return [event.model_dump(mode="json") for event in manager(request).require(task_id).events]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/review", response_model=TaskView)
async def review_task(task_id: str, payload: ReviewRequest, request: Request) -> TaskView:
    try:
        await manager(request).review(task_id, payload)
        return manager(request).view(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{task_id}/stream")
async def stream_task(task_id: str, request: Request) -> StreamingResponse:
    task_manager = manager(request)
    try:
        task_manager.require(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def events() -> AsyncIterator[str]:
        cursor = 0
        while True:
            task = task_manager.require(task_id)
            while cursor < len(task.events):
                event = task.events[cursor]
                cursor += 1
                yield f"event: {event.event}\ndata: {json.dumps(event.model_dump(mode='json'))}\n\n"
            if task.status in {"awaiting_human_review", "completed", "rejected", "failed"}:
                break
            if await request.is_disconnected():
                break
            await asyncio.sleep(0.1)

    return StreamingResponse(events(), media_type="text/event-stream")
