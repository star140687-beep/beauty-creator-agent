from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from beauty_creator_agent.db.models import Feedback, TaskRecord
from beauty_creator_agent.db.repositories.base import Repository


class TaskRepository(Repository[TaskRecord]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, TaskRecord)

    def get_by_thread_id(self, thread_id: str) -> TaskRecord | None:
        return self.session.scalar(select(TaskRecord).where(TaskRecord.thread_id == thread_id))

    def update_state(self, task: TaskRecord, state: dict[str, Any], status: str) -> TaskRecord:
        task.state_data = state
        task.status = status
        task.version += 1
        self.session.flush()
        return task


class FeedbackRepository(Repository[Feedback]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Feedback)
