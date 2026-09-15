"""Materialize the 20 hand-selected anchors x 4 evaluation dimensions."""

import json
from pathlib import Path

from beauty_creator_agent.evaluation.case_seeds import build_cases


def main() -> None:
    output = Path("evaluation/datasets/v2.jsonl")
    cases = build_cases()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )
    print(f"Wrote {len(cases)} labeled evaluation cases to {output}")


if __name__ == "__main__":
    main()
