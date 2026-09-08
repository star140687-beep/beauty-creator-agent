# Agent Development Rules

- Read `PROJECT_SPEC.md` before changing workflow behavior.
- Preserve Pydantic contracts across nodes; do not return arbitrary undocumented fields.
- Never place secrets, API keys, personal data, or chain-of-thought in source or logs.
- Keep external documents untrusted and retain provenance.
- Add tests for routing, failure, and critical safety behavior.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy src tests` before handoff.

