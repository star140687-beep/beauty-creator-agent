from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from beauty_creator_agent.db.models import ConsumerReview, ContentExample, Product
from beauty_creator_agent.db.repositories.base import Repository


class ProductRepository(Repository[Product]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Product)

    def upsert(self, values: dict[str, Any]) -> Product:
        entity = self.session.scalar(
            select(Product).where(Product.source_id == values["source_id"])
        )
        if entity is None:
            entity = Product(**values)
            self.session.add(entity)
        else:
            for key, value in values.items():
                setattr(entity, key, value)
        self.session.flush()
        return entity


class ReviewRepository(Repository[ConsumerReview]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ConsumerReview)

    def upsert(self, values: dict[str, Any]) -> ConsumerReview:
        entity = self.session.scalar(
            select(ConsumerReview).where(ConsumerReview.source_id == values["source_id"])
        )
        if entity is None:
            entity = ConsumerReview(**values)
            self.session.add(entity)
        else:
            for key, value in values.items():
                setattr(entity, key, value)
        self.session.flush()
        return entity


class ContentRepository(Repository[ContentExample]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ContentExample)

    def upsert(self, values: dict[str, Any]) -> ContentExample:
        entity = self.session.scalar(
            select(ContentExample).where(ContentExample.source_id == values["source_id"])
        )
        if entity is None:
            entity = ContentExample(**values)
            self.session.add(entity)
        else:
            for key, value in values.items():
                setattr(entity, key, value)
        self.session.flush()
        return entity
