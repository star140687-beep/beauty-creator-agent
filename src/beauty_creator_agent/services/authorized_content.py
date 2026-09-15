"""Normalize rights-cleared platform examples from local JSONL."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import HttpUrl, TypeAdapter

from beauty_creator_agent.schemas.ingestion import NormalizedContent

_URL = TypeAdapter(HttpUrl)


def content_rows(
    path: Path, *, source_name: str, license_name: str
) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                record = NormalizedContent.model_validate(
                    {**{key: value for key, value in raw.items() if key != "source_url"},
                     "source": source_name}
                )
                if not raw.get("source_url"):
                    raise ValueError("source_url is required")
                source_url = str(_URL.validate_python(raw["source_url"]))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{path}:{line_number}: invalid content record") from exc
            yield {
                **record.model_dump(),
                "source_metadata": {
                    "source_url": source_url,
                    "license": license_name,
                    "rights_status": "operator_confirmed",
                },
            }
