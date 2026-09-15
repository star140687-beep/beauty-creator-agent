import json
from pathlib import Path

import pytest

from beauty_creator_agent.evaluation.formal import (
    FORMAL_BASELINES,
    FORMAL_TOTAL_CASES,
    FormalDatasetError,
    grounding_rate,
    load_formal_dataset,
    load_retrieval_cases,
    ratio,
)


def _row(identifier: str, retriever: str) -> dict[str, object]:
    return {
        "id": identifier,
        "kind": "retrieval",
        "retriever": retriever,
        "query": "semantic concern query",
        "filters": {"query": "semantic concern query"},
        "gold_source_ids": [f"gold:{identifier}"],
    }


def test_formal_retrieval_cases_require_all_three_retrievers(tmp_path: Path) -> None:
    dataset = tmp_path / "formal.jsonl"
    rows = [
        _row("product_01", "product"),
        _row("review_01", "review"),
        _row("content_01", "content"),
    ]
    dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    cases, digest = load_retrieval_cases(dataset)

    assert len(cases) == 3
    assert len(digest) == 64
    assert {case.retriever for case in cases} == {"product", "review", "content"}


def test_formal_retrieval_cases_reject_missing_retriever_coverage(tmp_path: Path) -> None:
    dataset = tmp_path / "formal.jsonl"
    dataset.write_text(json.dumps(_row("product_01", "product")) + "\n", encoding="utf-8")

    with pytest.raises(FormalDatasetError, match="must cover"):
        load_retrieval_cases(dataset)


def _formal_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    rows.extend(
        {
            "id": f"routing_{index:02d}",
            "kind": "routing",
            "query": "create a marketing brief",
            "gold_route": "content_generation",
        }
        for index in range(25)
    )
    retrievers = ("product", "review", "content")
    rows.extend(
        _row(f"retrieval_{index:02d}", retrievers[index % len(retrievers)])
        for index in range(25)
    )
    rows.extend(
        {
            "id": f"generation_{index:02d}",
            "kind": "generation",
            "request": {"brief": "draft content"},
            "evidence_source_ids": [f"official:{index}"],
        }
        for index in range(15)
    )
    rows.extend(
        {
            "id": f"compliance_{index:02d}",
            "kind": "compliance",
            "market": "CN",
            "text": "marketing text",
            "gold_risk_labels": ["absolute_claim"] if index % 2 else [],
        }
        for index in range(15)
    )
    return rows


def test_formal_dataset_requires_exact_25_25_15_15_split(tmp_path: Path) -> None:
    dataset = tmp_path / "formal-v3.jsonl"
    rows = _formal_rows()
    dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    formal = load_formal_dataset(dataset)

    assert len(formal.cases) == FORMAL_TOTAL_CASES == 80
    assert formal.cohort_counts == {
        "routing": 25,
        "retrieval": 25,
        "generation": 15,
        "compliance": 15,
    }


def test_metric_helpers_calculate_without_claiming_a_measured_result() -> None:
    assert ratio(23, 25) == 0.92
    assert ratio(21, 25) == 0.84
    assert grounding_rate(0, 0) is None


def test_baseline_configurations_are_explicit_and_distinct() -> None:
    configurations = {configuration.name: configuration for configuration in FORMAL_BASELINES}

    assert set(configurations) == {"single_llm", "llm_plus_rag", "full_rag_agent"}
    assert not configurations["single_llm"].uses_retrieval
    assert configurations["llm_plus_rag"].uses_evidence_context
    assert configurations["full_rag_agent"].uses_claim_verification
