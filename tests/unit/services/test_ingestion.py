from pathlib import Path

from beauty_creator_agent.schemas.ingestion import NormalizedReview
from beauty_creator_agent.services.ingestion import (
    deduplicate,
    load_raw_jsonl,
    normalize_sample_product,
)


def test_sample_files_normalize_and_have_stable_provenance() -> None:
    products = [
        normalize_sample_product(row) for row in load_raw_jsonl(Path("data/samples/products.jsonl"))
    ]

    assert len(products) == 10
    assert all(product.source_id.startswith("sample_product_") for product in products)


def test_real_product_snapshot_normalizes_with_stable_provenance() -> None:
    products = [
        normalize_sample_product(row)
        for row in load_raw_jsonl(Path("data/openbeautyfacts/products.jsonl"))
    ]

    assert len(products) >= 20
    assert all(product.source == "open_beauty_facts" for product in products)


def test_deduplicate_is_idempotent_by_source_id() -> None:
    review = NormalizedReview(
        source_id="same",
        brand="Demo",
        product_name="Serum",
        category="serum",
        rating=4,
        review_text="Good",
        recommended=True,
        source="sample",
    )

    assert deduplicate([review, review]) == [review]
