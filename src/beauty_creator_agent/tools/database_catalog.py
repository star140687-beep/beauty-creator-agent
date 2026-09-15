"""Bounded, typed PostgreSQL catalog queries for large local datasets."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from beauty_creator_agent.db.models import ConsumerReview, ContentExample, Product
from beauty_creator_agent.tools.contracts import (
    ContentSearchQuery,
    ReviewStatisticsQuery,
    SearchQuery,
    SemanticSearchQuery,
    ToolResult,
)


def _row(entity: Product | ConsumerReview | ContentExample) -> dict[str, Any]:
    if isinstance(entity, Product):
        return {
            "source_id": entity.source_id,
            "source": entity.source,
            "source_metadata": entity.source_metadata,
            "brand": entity.brand,
            "product_name": entity.name,
            "category": entity.category,
            "description": entity.description,
            "claims": entity.claims,
        }
    if isinstance(entity, ConsumerReview):
        return {
            "source_id": entity.source_id,
            "source": entity.source,
            "source_metadata": entity.source_metadata,
            "brand": entity.brand,
            "product_name": entity.product_name,
            "category": entity.category,
            "review_text": entity.review_text,
        }
    return {
        "source_id": entity.source_id,
        "source": entity.source,
        "source_metadata": entity.source_metadata,
        "platform": entity.platform,
        "category": entity.category,
        "title": entity.title,
        "body": entity.body,
    }


def _result(rows: list[dict[str, Any]]) -> ToolResult:
    return ToolResult(ok=True, data=rows, source_ids=[row["source_id"] for row in rows])


class DatabaseCatalogTools:
    """Use indexed product names and bounded results instead of scanning 1M rows."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory

    def search_product_knowledge(self, query: SearchQuery) -> ToolResult:
        with self.factory() as session:
            entities = session.scalars(
                select(Product)
                .where(Product.name == query.query, Product.source != "sample")
                .order_by(Product.source_id)
                .limit(query.limit)
            ).all()
            return _result([_row(entity) for entity in entities])

    def semantic_search_products(
        self, query: SemanticSearchQuery, embedding: list[float]
    ) -> ToolResult:
        """Use pgvector cosine distance plus explicit filters for formal evaluation."""
        with self.factory() as session:
            statement = select(Product).where(
                Product.embedding.is_not(None), Product.source != "sample"
            )
            if query.brand:
                statement = statement.where(Product.brand == query.brand)
            if query.category:
                statement = statement.where(Product.category == query.category)
            entities = session.scalars(
                statement.order_by(Product.embedding.cosine_distance(embedding)).limit(query.limit)
            ).all()
            return _result([_row(entity) for entity in entities])

    def search_consumer_reviews(self, query: SearchQuery) -> ToolResult:
        with self.factory() as session:
            entities = session.scalars(
                select(ConsumerReview)
                .where(
                    ConsumerReview.product_name == query.query,
                    ConsumerReview.source != "sample",
                )
                .order_by(ConsumerReview.source_id)
                .limit(query.limit)
            ).all()
            return _result([_row(entity) for entity in entities])

    def semantic_search_reviews(
        self, query: SemanticSearchQuery, embedding: list[float]
    ) -> ToolResult:
        """Use pgvector cosine distance plus review metadata filters."""
        with self.factory() as session:
            statement = select(ConsumerReview).where(
                ConsumerReview.embedding.is_not(None), ConsumerReview.source != "sample"
            )
            if query.brand:
                statement = statement.where(ConsumerReview.brand == query.brand)
            if query.category:
                statement = statement.where(ConsumerReview.category == query.category)
            if query.skin_type:
                statement = statement.where(ConsumerReview.skin_type == query.skin_type)
            if query.rating_min is not None:
                statement = statement.where(ConsumerReview.rating >= query.rating_min)
            entities = session.scalars(
                statement.order_by(ConsumerReview.embedding.cosine_distance(embedding)).limit(query.limit)
            ).all()
            return _result([_row(entity) for entity in entities])

    def search_content_examples(self, query: ContentSearchQuery) -> ToolResult:
        with self.factory() as session:
            entities = session.scalars(
                select(ContentExample)
                .where(
                    ContentExample.platform == query.platform,
                    ContentExample.category == query.query,
                    ContentExample.source != "sample",
                )
                .order_by(ContentExample.source_id)
                .limit(query.limit)
            ).all()
            return _result([_row(entity) for entity in entities])

    def semantic_search_content(
        self, query: SemanticSearchQuery, embedding: list[float]
    ) -> ToolResult:
        """Use pgvector cosine distance plus platform/category filters."""
        with self.factory() as session:
            statement = select(ContentExample).where(
                ContentExample.embedding.is_not(None), ContentExample.source != "sample"
            )
            if query.category:
                statement = statement.where(ContentExample.category == query.category)
            if query.platform:
                statement = statement.where(ContentExample.platform == query.platform)
            entities = session.scalars(
                statement.order_by(ContentExample.embedding.cosine_distance(embedding)).limit(query.limit)
            ).all()
            return _result([_row(entity) for entity in entities])

    def get_review_statistics(self, query: ReviewStatisticsQuery) -> ToolResult:
        with self.factory() as session:
            statement = select(
                func.count(ConsumerReview.id), func.avg(ConsumerReview.rating)
            ).where(
                ConsumerReview.product_name == query.product_name,
                ConsumerReview.source != "sample",
            )
            if query.skin_type is not None:
                statement = statement.where(ConsumerReview.skin_type == query.skin_type)
            count, average = session.execute(statement).one()
            return ToolResult(
                ok=True,
                data={
                    "count": count,
                    "average_rating": round(float(average), 2) if average else None,
                },
            )
