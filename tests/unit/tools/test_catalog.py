import json
from pathlib import Path
from typing import Any

from beauty_creator_agent.tools.catalog import CatalogTools
from beauty_creator_agent.tools.contracts import (
    ContentSearchQuery,
    ReviewStatisticsQuery,
    SearchQuery,
)


def rows(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def tools() -> CatalogTools:
    return CatalogTools(
        products=rows("data/samples/products.jsonl"),
        reviews=rows("data/samples/reviews.jsonl"),
        content=rows("data/samples/content_examples.jsonl"),
    )


def test_product_search_returns_source_ids() -> None:
    result = tools().search_product_knowledge(SearchQuery(query="屏障修护精华"))

    assert result.ok
    assert "sample_product_001" in result.source_ids


def test_review_statistics_are_structured() -> None:
    result = tools().get_review_statistics(ReviewStatisticsQuery(product_name="屏障修护精华"))

    assert result.data == {"count": 2, "average_rating": 4.5}
    assert len(result.source_ids) == 2


def test_content_search_is_platform_scoped() -> None:
    result = tools().search_content_examples(
        ContentSearchQuery(query="精华", platform="xiaohongshu")
    )

    assert result.ok
    assert result.source_ids
