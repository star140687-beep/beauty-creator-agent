import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from beauty_creator_agent.schemas.ingestion import NormalizedProduct


def read_jsonl[RecordT: BaseModel](path: Path, model: type[RecordT]) -> list[RecordT]:
    records: list[RecordT] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    records.append(model.model_validate_json(line))
                except ValueError as exc:
                    raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return records


def deduplicate[RecordT: BaseModel](records: Iterable[RecordT]) -> list[RecordT]:
    unique: dict[str, RecordT] = {}
    for record in records:
        source_id = getattr(record, "source_id", None)
        if not isinstance(source_id, str):
            raise ValueError("normalized record must have source_id")
        unique[source_id] = record
    return list(unique.values())


def normalize_sample_product(raw: dict[str, Any]) -> NormalizedProduct:
    return NormalizedProduct(
        source_id=raw["source_id"],
        brand=raw["brand"],
        name=raw["product_name"],
        category=raw["category"],
        description=raw["description"],
        ingredients=raw.get("ingredients", []),
        skin_types=raw.get("skin_types", []),
        claims=raw.get("claims", []),
        official_url=raw.get("official_url"),
        source=raw["source"],
    )


def load_raw_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
