from pathlib import Path

import pytest

from beauty_creator_agent.services.authorized_content import content_rows


def test_authorized_content_requires_source_url(tmp_path: Path) -> None:
    path = tmp_path / "content.jsonl"
    path.write_text(
        '{"source_id":"owned:1","platform":"xiaohongshu","category":"serum",'
        '"title":"A title","body":"A body","content_pattern":"guide","tone":"neutral"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid content record"):
        list(content_rows(path, source_name="owned", license_name="owned"))


def test_authorized_content_keeps_rights_provenance(tmp_path: Path) -> None:
    path = tmp_path / "content.jsonl"
    path.write_text(
        '{"source_id":"owned:1","platform":"xiaohongshu","category":"serum",'
        '"title":"A title","body":"A body","content_pattern":"guide",'
        '"tone":"neutral","source_url":"https://example.com/1"}\n',
        encoding="utf-8",
    )

    record = next(content_rows(path, source_name="brand_owned", license_name="owned"))

    assert record["source"] == "brand_owned"
    assert record["source_metadata"]["source_url"] == "https://example.com/1"
    assert record["source_metadata"]["license"] == "owned"


def test_authorized_content_rejects_non_url_provenance(tmp_path: Path) -> None:
    path = tmp_path / "content.jsonl"
    path.write_text(
        '{"source_id":"owned:1","platform":"xiaohongshu","category":"serum",'
        '"title":"A title","body":"A body","content_pattern":"guide",'
        '"tone":"neutral","source_url":"not a url"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid content record"):
        list(content_rows(path, source_name="owned", license_name="owned"))
