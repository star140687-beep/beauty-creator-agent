"""Batch, idempotent PostgreSQL import for normalized catalog records."""

from collections.abc import Iterable
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from beauty_creator_agent.db.models import ConsumerReview, ContentExample, Product

CatalogModel = type[Product] | type[ConsumerReview] | type[ContentExample]


def batches(
    records: Iterable[dict[str, Any]], size: int, limit: int | None = None
) -> Iterable[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    seen = 0
    for record in records:
        if limit is not None and seen >= limit:
            break
        batch.append(record)
        seen += 1
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def upsert_batch(session: Session, model: CatalogModel, batch: list[dict[str, Any]]) -> None:
    unique = {record["source_id"]: record for record in batch}
    if not unique:
        return
    statement = insert(model).values(list(unique.values()))
    update = {
        key: statement.excluded[key]
        for key in unique[next(iter(unique))]
        if key not in {"id", "source_id", "created_at"}
    }
    session.execute(statement.on_conflict_do_update(index_elements=[model.source_id], set_=update))


def import_rows(
    session: Session | None,
    model: CatalogModel,
    records: Iterable[dict[str, Any]],
    *,
    batch_size: int,
    limit: int | None,
) -> int:
    count = 0
    for batch in batches(records, batch_size, limit):
        if session is not None:
            upsert_batch(session, model, batch)
            session.commit()
        count += len(batch)
    return count
