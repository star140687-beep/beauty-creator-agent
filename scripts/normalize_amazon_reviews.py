import argparse
import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from beauty_creator_agent.services.real_data import normalize_amazon_review


def lines(path: Path) -> Iterator[str]:
    if path.suffix == ".gz":
        with gzip.open(path, mode="rt", encoding="utf-8") as handle:
            yield from handle
    else:
        with path.open(encoding="utf-8") as handle:
            yield from handle


def write_subset(source: Path, output: TextIO, limit: int) -> int:
    count = 0
    for line in lines(source):
        record = normalize_amazon_review(json.loads(line))
        if record is None:
            continue
        output.write(json.dumps(record, ensure_ascii=False) + "\n")
        count += 1
        if count >= limit:
            break
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local, de-identified research subset")
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/amazon_beauty_reviews.jsonl")
    )
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        count = write_subset(args.source, output, args.limit)
    print(f"Wrote {count} de-identified reviews to {args.output}")


if __name__ == "__main__":
    main()
