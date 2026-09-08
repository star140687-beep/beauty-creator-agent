from sqlalchemy import select
from sqlalchemy.orm import Session

from beauty_creator_agent.db.base import Base


class Repository[ModelT: Base]:
    """Small typed repository; graph nodes never issue SQL directly."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get(self, entity_id: str) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()
        return entity

    def list(self, *, limit: int = 100) -> list[ModelT]:
        statement = select(self.model).limit(limit)
        return list(self.session.scalars(statement))
