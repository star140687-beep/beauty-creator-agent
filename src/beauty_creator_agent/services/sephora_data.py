"""Streaming adapters for the locally supplied Sephora dataset.

These adapters do not retain reviewer identifiers or treat scraped listings as
manufacturer-verified product claims.
"""

import ast
import csv
import hashlib
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from beauty_creator_agent.schemas.ingestion import NormalizedProduct, NormalizedReview

DATASET_URL = "https://www.kaggle.com/datasets/nadyinky/sephora-products-and-skincare-reviews"
DATASET_LICENSE = "CC-BY-4.0"
SOURCE = "sephora_kaggle_2023"

_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{8,}\d)(?!\w)")
_URL = re.compile(r"https?://\S+", flags=re.IGNORECASE)


def _rows(path: Path) -> Iterator[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        csv.field_size_limit(2_000_000)
        yield from csv.DictReader(handle)


def scrub_review_text(text: str) -> str:
    """Remove common direct identifiers before storage; not a PII guarantee."""
    text = _EMAIL.sub("[email removed]", text)
    text = _PHONE.sub("[phone removed]", text)
    return _URL.sub("[link removed]", text).strip()


def _ingredients(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    if not isinstance(value, list):
        return []
    return [item[:300] for item in value[:80] if isinstance(item, str) and item.strip()]


def products(path: Path) -> Iterator[dict[str, Any]]:
    for row in _rows(path):
        product_id = (row.get("product_id") or "").strip()
        name = (row.get("product_name") or "").strip()
        brand = (row.get("brand_name") or "").strip()
        if not product_id or not name or not brand:
            continue
        record = NormalizedProduct(
            source_id=f"sephora-product:{product_id}",
            brand=brand,
            name=name,
            category=(row.get("primary_category") or "beauty").strip() or "beauty",
            description=(
                f"Third-party dataset listing for {name} by {brand}; not manufacturer verified."
            ),
            ingredients=_ingredients(row.get("ingredients") or ""),
            claims=[],
            official_url=None,
            source=SOURCE,
        )
        yield {
            **record.model_dump(),
            "source_metadata": {
                "dataset_url": DATASET_URL,
                "license": DATASET_LICENSE,
                "product_id": product_id,
                "verification": "third_party_unverified",
            },
        }


def reviews(path: Path) -> Iterator[dict[str, Any]]:
    for row in _rows(path):
        product_id = (row.get("product_id") or "").strip()
        name = (row.get("product_name") or "").strip()
        brand = (row.get("brand_name") or "").strip()
        text = scrub_review_text((row.get("review_text") or "").strip())
        if not product_id or not name or not brand or not text:
            continue
        try:
            rating = float(row.get("rating") or "")
        except ValueError:
            continue
        flag = (row.get("is_recommended_eda") or row.get("is_recommended") or "").strip()
        recommended = {"1": True, "1.0": True, "0": False, "0.0": False}.get(flag)
        date = (row.get("submission_time") or "").strip()
        fingerprint = hashlib.sha256(
            "\x1f".join((product_id, date, text)).encode("utf-8")
        ).hexdigest()[:32]
        try:
            record = NormalizedReview(
                source_id=f"sephora-review:{fingerprint}",
                brand=brand,
                product_name=name,
                category="skincare",
                skin_type=None,
                rating=rating,
                review_text=text[:10_000],
                recommended=recommended,
                source=SOURCE,
            )
        except ValueError:
            continue
        yield {
            **record.model_dump(),
            "source_metadata": {
                "dataset_url": DATASET_URL,
                "license": DATASET_LICENSE,
                "product_id": product_id,
                "submission_time": date,
                "direct_identifiers_removed": True,
            },
        }
