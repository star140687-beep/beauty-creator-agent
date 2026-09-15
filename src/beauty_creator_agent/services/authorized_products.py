"""Normalize operator-supplied, rights-cleared multi-brand product records."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import HttpUrl, TypeAdapter

from beauty_creator_agent.schemas.ingestion import NormalizedProduct

_URL = TypeAdapter(HttpUrl)


def product_rows(
    path: Path, *, source_name: str, license_name: str, manufacturer_documented: bool
) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                source_url = str(_URL.validate_python(raw["source_url"]))
                claim_evidence = raw.get("claim_evidence") or {}
                if not isinstance(claim_evidence, dict):
                    raise ValueError("claim_evidence must map claim text to evidence URLs")
                record = NormalizedProduct.model_validate(
                    {
                        **{
                            key: value
                            for key, value in raw.items()
                            if key not in {"source_url", "claim_evidence", "license"}
                        },
                        "source": source_name,
                    }
                )
                if record.claims and not manufacturer_documented:
                    raise ValueError("claims require explicit manufacturer documentation mode")
                if set(record.claims) != set(claim_evidence):
                    raise ValueError("every claim requires its own evidence URL")
                links = {
                    claim: str(_URL.validate_python(url))
                    for claim, url in claim_evidence.items()
                }
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: invalid product record") from exc
            yield {
                **record.model_dump(),
                "source_metadata": {
                    "source_url": source_url,
                    "license": license_name,
                    "verification": (
                        "operator_confirmed_manufacturer_documented"
                        if manufacturer_documented
                        else "third_party_unverified"
                    ),
                    "claim_evidence": links,
                    "rights_status": "operator_confirmed",
                },
            }
