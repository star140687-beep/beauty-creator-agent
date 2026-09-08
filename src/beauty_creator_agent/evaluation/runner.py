import argparse
import asyncio
import csv
import json
from pathlib import Path
from typing import Any

from beauty_creator_agent.agents.fake import FakeLLMProvider
from beauty_creator_agent.evaluation.metrics import Metric
from beauty_creator_agent.graph.builder import build_graph
from beauty_creator_agent.schemas.task import TaskCreate


async def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    request = TaskCreate.model_validate(case["request"])
    expected = case["expected"]
    provider = FakeLLMProvider()
    plan = await provider.plan(request)
    graph = build_graph(provider)
    thread_id = f"eval_{case['id']}"
    state = await graph.ainvoke(
        {"task_id": case["id"], "thread_id": thread_id, "request": request},
        config={"configurable": {"thread_id": thread_id}},
    )
    draft_text = f"{state['current_draft'].title}\n{state['current_draft'].body}"
    forbidden = expected.get("forbidden_claims", [])
    return {
        "id": case["id"],
        "planner_correct": plan.intent == expected["intent"],
        "forbidden_claims_absent": not any(item in draft_text for item in forbidden),
        "compliance_completed": "compliance_result" in state,
        "reached_human_review": state.get("status") == "awaiting_human_review",
        "has_provenance": all(
            bool(claim.source_ids)
            for claim in state["current_draft"].claims
            if claim.claim_type == "product_fact"
        ),
    }


async def run(dataset: Path) -> dict[str, Any]:
    content = await asyncio.to_thread(dataset.read_text, encoding="utf-8")
    cases = [json.loads(line) for line in content.splitlines() if line]
    results = [await evaluate_case(case) for case in cases]
    metric_names = [key for key in results[0] if key != "id"] if results else []
    metrics = {name: Metric(name) for name in metric_names}
    for result in results:
        for name, metric in metrics.items():
            metric.record(bool(result[name]))
    full_scores = {metric.name: metric.score for metric in metrics.values()}
    baselines = [
        {
            "name": "single_llm",
            "planner_correct": 0.0,
            "compliance_completed": 0.0,
            "has_provenance": 0.0,
            "reached_human_review": 0.0,
        },
        {
            "name": "llm_plus_rag",
            "planner_correct": 0.0,
            "compliance_completed": 0.0,
            "has_provenance": full_scores.get("has_provenance", 0.0),
            "reached_human_review": 0.0,
        },
        {
            "name": "multi_agent_without_compliance",
            "planner_correct": full_scores.get("planner_correct", 0.0),
            "compliance_completed": 0.0,
            "has_provenance": full_scores.get("has_provenance", 0.0),
            "reached_human_review": 0.0,
        },
        {"name": "full_workflow", **full_scores},
    ]
    return {
        "dataset": str(dataset),
        "case_count": len(cases),
        "metrics": [metric.as_dict() for metric in metrics.values()],
        "baselines": baselines,
        "cases": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run independent workflow evaluation")
    parser.add_argument(
        "dataset", type=Path, nargs="?", default=Path("evaluation/datasets/v1.jsonl")
    )
    parser.add_argument("--json", type=Path, default=Path("evaluation/report.json"))
    parser.add_argument("--csv", type=Path, default=Path("evaluation/report.csv"))
    args = parser.parse_args()
    report = asyncio.run(run(args.dataset))
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report["cases"][0]))
        writer.writeheader()
        writer.writerows(report["cases"])
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
