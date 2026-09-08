import re
from datetime import UTC, datetime
from typing import Any

import httpx

OPEN_BEAUTY_FACTS_API = "https://world.openbeautyfacts.org/cgi/search.pl"
OPEN_BEAUTY_FACTS_USER_AGENT = "BeautyCreatorAgent/0.1 (open-source research demo)"
CATEGORY_QUERIES = {
    "moisturizer": "moisturizer",
    "serum": "facial serum",
    "cleanser": "facial cleanser",
    "sunscreen": "sunscreen",
}


def normalize_openbeautyfacts(
    product: dict[str, Any], category: str, retrieved_at: str
) -> dict[str, Any] | None:
    code = str(product.get("code") or "").strip()
    name = str(product.get("product_name") or "").strip()
    brand = str(product.get("brands") or "").strip()
    ingredients_text = str(product.get("ingredients_text") or "").strip()
    if not code or not name or not brand or not ingredients_text:
        return None
    suspicious_contact = re.search(
        r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|toll[ -]?free|telephone|phone|contact us)",
        ingredients_text,
        flags=re.IGNORECASE,
    )
    if suspicious_contact or any(len(part.strip()) > 300 for part in ingredients_text.split(",")):
        return None
    ingredients = [item.strip() for item in ingredients_text.split(",") if item.strip()][:80]
    source_url = str(product.get("url") or f"https://world.openbeautyfacts.org/product/{code}")
    return {
        "id": f"obf_{code}",
        "brand": brand,
        "product_name": name,
        "category": category,
        "description": f"Open Beauty Facts crowdsourced record for {name} by {brand}.",
        "ingredients": ingredients,
        "skin_types": [],
        "claims": [],
        "official_url": None,
        "source": "open_beauty_facts",
        "source_id": f"openbeautyfacts:{code}",
        "source_url": source_url,
        "barcode": code,
        "retrieved_at": retrieved_at,
        "license": "ODbL-1.0",
    }


def download_openbeautyfacts(*, per_category: int) -> list[dict[str, Any]]:
    retrieved_at = datetime.now(UTC).isoformat()
    records: dict[str, dict[str, Any]] = {}
    headers = {"User-Agent": OPEN_BEAUTY_FACTS_USER_AGENT}
    with httpx.Client(headers=headers, timeout=60, follow_redirects=True) as client:
        for category, query in CATEGORY_QUERIES.items():
            response = client.get(
                OPEN_BEAUTY_FACTS_API,
                params={
                    "search_terms": query,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": max(per_category * 4, 20),
                },
            )
            response.raise_for_status()
            accepted = 0
            for product in response.json().get("products", []):
                record = normalize_openbeautyfacts(product, category, retrieved_at)
                if record is None or record["source_id"] in records:
                    continue
                records[record["source_id"]] = record
                accepted += 1
                if accepted >= per_category:
                    break
    return sorted(records.values(), key=lambda item: item["source_id"])


def normalize_amazon_review(raw: dict[str, Any]) -> dict[str, Any] | None:
    text = str(raw.get("text") or raw.get("reviewText") or "").strip()
    product_id = str(raw.get("parent_asin") or raw.get("asin") or "").strip()
    rating = raw.get("rating", raw.get("overall"))
    if not text or not product_id or not isinstance(rating, (int, float)):
        return None
    return {
        "brand": "unknown",
        "product_name": product_id,
        "category": "beauty",
        "skin_type": None,
        "rating": float(rating),
        "review_text": text,
        "recommended": None,
        "source": "amazon_reviews_2023_research",
        "source_id": f"amazon-review:{product_id}:{raw.get('timestamp', 'unknown')}",
    }
