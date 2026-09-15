from typing import Any

from sqlalchemy.dialects import postgresql

from beauty_creator_agent.db.models import ConsumerReview
from beauty_creator_agent.services.bulk_import import batches, import_rows, upsert_batch


class RecordingSession:
    def __init__(self) -> None:
        self.statements: list[Any] = []
        self.commits = 0

    def execute(self, statement: Any) -> None:
        self.statements.append(statement)

    def commit(self) -> None:
        self.commits += 1


def test_batches_limit_streaming_without_loading_all_records() -> None:
    inspected: list[int] = []

    def stream() -> Any:
        for number in range(100):
            inspected.append(number)
            yield {"source_id": str(number)}

    result = list(batches(stream(), 2, 5))

    assert [len(batch) for batch in result] == [2, 2, 1]
    assert len(inspected) <= 6


def test_upsert_deduplicates_one_batch_and_uses_source_id_conflict() -> None:
    session = RecordingSession()
    rows = [
        {
            "source_id": "same",
            "brand": "Example",
            "product_name": "Serum",
            "category": "skincare",
            "rating": 4.0,
            "review_text": "Good",
            "source": "sephora_kaggle_2023",
        }
    ] * 2

    upsert_batch(session, ConsumerReview, rows)  # type: ignore[arg-type]

    assert len(session.statements) == 1
    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
    assert "ON CONFLICT (source_id) DO UPDATE" in sql
    assert sql.count("source_id") > 0


def test_dry_run_import_never_writes_database() -> None:
    rows = ({"source_id": str(i)} for i in range(10))

    assert import_rows(None, ConsumerReview, rows, batch_size=3, limit=5) == 5
