from pathlib import Path

import pytest

from beauty_creator_agent.evaluation.runner import run


@pytest.mark.asyncio
async def test_evaluation_pipeline_returns_machine_readable_metrics() -> None:
    report = await run(Path("evaluation/datasets/v1.jsonl"))

    assert report["case_count"] == 5
    assert len(report["metrics"]) == 5
    assert all(0 <= metric["score"] <= 1 for metric in report["metrics"])
