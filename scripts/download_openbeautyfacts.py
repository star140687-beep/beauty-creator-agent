import argparse
import json
from pathlib import Path

from beauty_creator_agent.services.real_data import download_openbeautyfacts


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
    content = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records)
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote {len(records)} licensed records to {args.output}")


if __name__ == "__main__":
    main()
