import time

from fastapi.testclient import TestClient

from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.main import app
from beauty_creator_agent.services.tasks import TaskManager


def test_task_api_create_poll_and_review() -> None:
    app.state.task_manager = TaskManager(FakeLLMProvider())
    client = TestClient(app)
    response = client.post(
        "/v1/tasks",
        json={
            "product": {"name": "Barrier Serum"},
            "platform": "xiaohongshu",
            "objective": "Generate content",
        },
    )

    assert response.status_code == 202
    task_id = response.json()["task_id"]
    task = response.json()
    for _ in range(50):
        task = client.get(f"/v1/tasks/{task_id}").json()
        if task["status"] == "awaiting_human_review":
            break
        time.sleep(0.01)

    assert task["status"] == "awaiting_human_review"
    history = client.get(f"/v1/tasks/{task_id}/history")
    assert history.status_code == 200
    assert history.json()[-1]["event"] == "human_review.required"

    reviewed = client.post(f"/v1/tasks/{task_id}/review", json={"action": "approve"})
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "completed"


def test_unknown_task_returns_404() -> None:
    app.state.task_manager = TaskManager(FakeLLMProvider())

    assert TestClient(app).get("/v1/tasks/missing").status_code == 404
