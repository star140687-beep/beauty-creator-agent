"""Write public, non-personal brand counts from the local multi-brand dataset."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from beauty_creator_agent.services.brand_coverage import summarize_brands
from beauty_creator_agent.services.sephora_data import (
    DATASET_LICENSE,
    DATASET_URL,
    products,
    reviews,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate multi-brand product/review coverage")
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("data/coverage/multibrand_coverage.json")
    )
    args = parser.parse_args()
    for path in (args.products, args.reviews):
        if not path.is_file():
            parser.error(f"source file not found: {path}")
    report = {
        "dataset_url": DATASET_URL,
        "license": DATASET_LICENSE,
        "checked_at": datetime.now(UTC).date().isoformat(),
        "records_published": "aggregate_counts_only",
        **summarize_brands(products(args.products), reviews(args.reviews)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Counted {report['product_records']} products and {report['review_records']} "
        f"reviews across {report['product_brands']} product brands"
    )


if __name__ == "__main__":
    main()
