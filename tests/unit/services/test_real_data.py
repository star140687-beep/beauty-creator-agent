import json
from pathlib import Path

from beauty_creator_agent.services.real_data import (
    normalize_amazon_review,
    normalize_openbeautyfacts,
)


def test_openbeautyfacts_snapshot_has_license_and_provenance() -> None:
    path = Path("data/openbeautyfacts/products.jsonl")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert len(records) >= 20
    assert len({record["barcode"] for record in records}) == len(records)
    assert all(record["license"] == "ODbL-1.0" for record in records)
    assert all(record["source_id"].startswith("openbeautyfacts:") for record in records)
    assert all(record["source_url"].startswith("https://") for record in records)
    assert all(record["claims"] == [] for record in records)


def test_openbeautyfacts_normalizer_rejects_incomplete_records() -> None:
    assert (
        normalize_openbeautyfacts({"code": "1", "product_name": "Incomplete"}, "serum", "now")
        is None
    )


def test_openbeautyfacts_normalizer_rejects_contact_details_in_ocr() -> None:
    assert (
        normalize_openbeautyfacts(
            {
                "code": "1",
                "product_name": "Bad OCR",
                "brands": "Example",
                "ingredients_text": "Water, call toll free 1800, help@example.com",
            },
            "serum",
            "now",
        )
        is None
    )


def test_review_normalizer_drops_personal_identifiers() -> None:
    result = normalize_amazon_review(
        {
            "user_id": "private-user",
            "reviewerName": "Private Person",
            "parent_asin": "B001",
            "rating": 4,
            "text": "Works well",
            "timestamp": 123,
        }
    )

    assert result is not None
    assert "user_id" not in result
    assert "reviewerName" not in result
    assert result["source_id"] == "amazon-review:B001:123"
