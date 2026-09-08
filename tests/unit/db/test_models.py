from beauty_creator_agent.db import models  # noqa: F401
from beauty_creator_agent.db.base import Base


def test_expected_tables_are_registered() -> None:
    assert {"products", "consumer_reviews", "content_examples", "tasks", "feedback"} <= set(
        Base.metadata.tables
    )
