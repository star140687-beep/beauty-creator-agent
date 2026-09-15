from pathlib import Path

import pytest

from beauty_creator_agent.services.authorized_products import product_rows
from beauty_creator_agent.services.research import ResearchService


def _product_json(*, claim_evidence: str = "{}") -> str:
    return (
        '{"source_id":"brand:sku-1","brand":"Brand A","name":"Serum A",'
        '"category":"serum","description":"A documented listing",'
        '"claims":["Contains ceramides"],'
        f'"claim_evidence":{claim_evidence},'
        '"source_url":"https://example.com/products/sku-1"}\n'
    )


def test_authorized_product_rejects_claim_without_document(tmp_path: Path) -> None:
    path = tmp_path / "products.jsonl"
    path.write_text(_product_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid product record"):
        list(
            product_rows(
                path,
                source_name="brand_owned",
                license_name="owned",
                manufacturer_documented=True,
            )
        )


def test_authorized_product_requires_explicit_documented_mode(tmp_path: Path) -> None:
    path = tmp_path / "products.jsonl"
    path.write_text(
        _product_json(
            claim_evidence='{"Contains ceramides":"https://example.com/evidence/sku-1"}'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid product record"):
        list(
            product_rows(
                path,
                source_name="brand_owned",
                license_name="owned",
                manufacturer_documented=False,
            )
        )


def test_documented_claim_produces_separate_traceable_evidence(tmp_path: Path) -> None:
    path = tmp_path / "products.jsonl"
    path.write_text(
        _product_json(
            claim_evidence='{"Contains ceramides":"https://example.com/evidence/sku-1"}'
        ),
        encoding="utf-8",
    )
    row = next(
        product_rows(
            path,
            source_name="brand_owned",
            license_name="owned",
            manufacturer_documented=True,
        )
    )
    row["product_name"] = row.pop("name")

    evidence = ResearchService._to_evidence([row], "product_fact", "external_search")

    assert len(evidence) == 2
    assert evidence[1].source_type == "official"
    assert evidence[1].source_id and evidence[1].source_id.startswith("brand:sku-1:claim:")
    assert evidence[1].metadata["evidence_url"] == "https://example.com/evidence/sku-1"
