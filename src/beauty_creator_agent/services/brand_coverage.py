"""Aggregate brand coverage without publishing review bodies or reviewer fields."""

from collections import Counter
from collections.abc import Iterable
from typing import Any


def summarize_brands(
    product_rows: Iterable[dict[str, Any]], review_rows: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    products = Counter(row["brand"] for row in product_rows)
    reviews = Counter(row["brand"] for row in review_rows)
    names = sorted(products.keys() | reviews.keys(), key=str.casefold)
    return {
        "product_records": sum(products.values()),
        "review_records": sum(reviews.values()),
        "product_brands": len(products),
        "review_brands": len(reviews),
        "brands": [
            {
                "brand": name,
                "product_records": products[name],
                "review_records": reviews[name],
            }
            for name in names
        ],
    }
