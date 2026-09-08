from collections.abc import Sequence
from typing import Any

from beauty_creator_agent.tools.contracts import (
    ContentSearchQuery,
    ReviewStatisticsQuery,
    SearchQuery,
    ToolResult,
)


def _search(
    rows: Sequence[dict[str, Any]], query: str, fields: tuple[str, ...], limit: int
) -> ToolResult:
    terms = query.casefold().split()
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        haystack = " ".join(str(row.get(field, "")) for field in fields).casefold()
        score = sum(term in haystack for term in terms)
        if score:
            scored.append((score, row))
    matches = [row for _, row in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]
    return ToolResult(ok=True, data=matches, source_ids=[row["source_id"] for row in matches])


class CatalogTools:
    """Typed local tool layer; database-backed adapters can supply the same row shape."""

    def __init__(
        self,
        *,
        products: Sequence[dict[str, Any]],
        reviews: Sequence[dict[str, Any]],
        content: Sequence[dict[str, Any]],
    ) -> None:
        self.products = products
        self.reviews = reviews
        self.content = content

    def search_product_knowledge(self, query: SearchQuery) -> ToolResult:
        return _search(
            self.products, query.query, ("brand", "product_name", "description"), query.limit
        )

    def search_consumer_reviews(self, query: SearchQuery) -> ToolResult:
        return _search(
            self.reviews, query.query, ("brand", "product_name", "review_text"), query.limit
        )

    def search_content_examples(self, query: ContentSearchQuery) -> ToolResult:
        rows = [row for row in self.content if row.get("platform") == query.platform]
        return _search(rows, query.query, ("title", "body", "category"), query.limit)

    def get_review_statistics(self, query: ReviewStatisticsQuery) -> ToolResult:
        rows = [
            row
            for row in self.reviews
            if row.get("product_name") == query.product_name
            and (query.skin_type is None or row.get("skin_type") == query.skin_type)
        ]
        if not rows:
            return ToolResult(ok=True, data={"count": 0, "average_rating": None})
        average = sum(float(row["rating"]) for row in rows) / len(rows)
        return ToolResult(
            ok=True,
            data={"count": len(rows), "average_rating": round(average, 2)},
            source_ids=[row["source_id"] for row in rows],
        )
