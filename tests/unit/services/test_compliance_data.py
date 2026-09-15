import json
from pathlib import Path

from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.services.compliance import ComplianceSystem


def test_regulatory_catalog_has_unique_official_sources() -> None:
    records = [
        json.loads(line)
        for line in Path("data/compliance/regulatory_sources.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert len(records) == 5
    assert len({record["source_id"] for record in records}) == len(records)
    assert {record["market"] for record in records} == {"CN", "US", "EU"}
    assert all(record["source_url"].startswith("https://") for record in records)
    assert all(record["checked_at"] for record in records)


def test_executable_official_rules_have_source_links_and_market_scope() -> None:
    rules = ComplianceSystem(FakeLLMProvider()).rules
    source_ids = {
        json.loads(line)["source_id"]
        for line in Path("data/compliance/regulatory_sources.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    }

    assert len(rules) == 6
    assert len({rule.id for rule in rules}) == len(rules)
    assert all(rule.source_url for rule in rules if rule.source_kind == "official")
    assert all(
        rule.regulatory_source_id in source_ids
        for rule in rules
        if rule.source_kind == "official"
    )
    assert all(rule.markets for rule in rules)
    assert any(rule.source_kind == "internal_policy" for rule in rules)
