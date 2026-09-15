from unittest.mock import MagicMock

from beauty_creator_agent.tools.contracts import ContentSearchQuery, SearchQuery
from beauty_creator_agent.tools.database_catalog import DatabaseCatalogTools


def _catalog() -> tuple[DatabaseCatalogTools, MagicMock]:
    factory = MagicMock()
    session = MagicMock()
    factory.return_value.__enter__.return_value = session
    session.scalars.return_value.all.return_value = []
    return DatabaseCatalogTools(factory), session


def test_database_product_search_is_bounded_and_excludes_samples() -> None:
    catalog, session = _catalog()

    catalog.search_product_knowledge(SearchQuery(query="Serum", limit=5))

    statement = session.scalars.call_args.args[0]
    sql = str(statement)
    assert "products.name =" in sql
    assert "products.source !=" in sql
    assert "LIMIT" in sql


def test_database_content_search_requires_platform_and_category() -> None:
    catalog, session = _catalog()

    catalog.search_content_examples(
        ContentSearchQuery(query="serum", platform="xiaohongshu", limit=3)
    )

    sql = str(session.scalars.call_args.args[0])
    assert "content_examples.platform =" in sql
    assert "content_examples.category =" in sql
    assert "content_examples.source !=" in sql
    assert "LIMIT" in sql
