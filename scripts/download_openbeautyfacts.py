import argparse
import json
from pathlib import Path

from beauty_creator_agent.services.real_data import download_openbeautyfacts


def merge_existing(path: Path, records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Retain existing barcodes when refreshing a bounded public snapshot."""
    by_id: dict[str, dict[str, object]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    by_id[str(row["source_id"])] = row
    for row in records:
        by_id[str(row["source_id"])] = row
    return [by_id[key] for key in sorted(by_id)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a licensed Open Beauty Facts snapshot")
    parser.add_argument("--per-category", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("data/openbeautyfacts/products.jsonl"))
    args = parser.parse_args()
    if not 1 <= args.per_category <= 50:
        parser.error("--per-category must be between 1 and 50")
    records = download_openbeautyfacts(per_category=args.per_category)
    if not records:
        raise RuntimeError("Open Beauty Facts returned no complete product records")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    combined = merge_existing(args.output, records)
    content = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in combined)
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote {len(combined)} licensed records to {args.output}")


if __name__ == "__main__":
    main()
