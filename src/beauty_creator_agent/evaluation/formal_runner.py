"""CLI that validates the frozen formal dataset without running evaluation."""

import argparse
import json
from pathlib import Path

from beauty_creator_agent.evaluation.formal import (
    FORMAL_BASELINES,
    build_unmeasured_report,
    load_formal_dataset,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate formal evaluation dataset and runner setup"
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--dataset-version", default="formal-v3")
    args = parser.parse_args()
    dataset = load_formal_dataset(args.dataset)
    report = build_unmeasured_report(dataset, args.dataset_version)
    print(
        json.dumps(
            {
                "dataset_sha256": dataset.sha256,
                "cohort_counts": dataset.cohort_counts,
                "baseline_configurations": [
                    baseline.model_dump() for baseline in FORMAL_BASELINES
                ],
                "measurement_complete": report.measurement_complete,
                "message": "Dataset validation complete; no model, database, or benchmark was run.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
