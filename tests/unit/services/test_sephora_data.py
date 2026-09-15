import csv
from pathlib import Path

from beauty_creator_agent.services.sephora_data import products, reviews


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_product_adapter_keeps_provenance_but_no_verified_claims(tmp_path: Path) -> None:
    path = tmp_path / "product_info.csv"
    write_csv(
        path,
        [
            {
                "product_id": "P123",
                "product_name": "Hydrating Serum",
                "brand_name": "Example",
                "primary_category": "Skincare",
                "ingredients": "['Water', 'Glycerin']",
            }
        ],
    )

    item = next(products(path))

    assert item["source_id"] == "sephora-product:P123"
    assert item["claims"] == []
    assert item["official_url"] is None
    assert item["source_metadata"]["license"] == "CC-BY-4.0"
    assert item["source_metadata"]["verification"] == "third_party_unverified"


def test_review_adapter_drops_author_and_scrubs_direct_identifiers(tmp_path: Path) -> None:
    path = tmp_path / "reviews.csv"
    write_csv(
        path,
        [
            {
                "author_id": "private-123",
                "product_id": "P123",
                "product_name": "Hydrating Serum",
                "brand_name": "Example",
                "rating": "5",
                "submission_time": "2023-01-01",
                "review_text": "Works well. Contact me at user@example.com or +1 555 123 4567",
                "is_recommended_eda": "1.0",
                "eda_skin_type": "sensitive",
            }
        ],
    )

    first = next(reviews(path))
    second = next(reviews(path))

    assert first["source_id"] == second["source_id"]
    assert first["recommended"] is True
    assert first["skin_type"] is None
    assert "author_id" not in first and "private-123" not in str(first)
    assert "user@example.com" not in first["review_text"]
    assert "555 123 4567" not in first["review_text"]


def test_review_adapter_skips_invalid_rating(tmp_path: Path) -> None:
    path = tmp_path / "reviews.csv"
    write_csv(
        path,
        [
            {
                "product_id": "P123",
                "product_name": "Hydrating Serum",
                "brand_name": "Example",
                "rating": "7",
                "review_text": "Amazing",
            }
        ],
    )

    assert list(reviews(path)) == []
