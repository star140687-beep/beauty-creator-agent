# Project Specification

Beauty Creator Agent generates evidence-grounded beauty content through structured planning, research tools, writing, three-layer compliance, bounded revision, and human approval.

## Invariants

- External facts enter through typed tools and retain `source_id` provenance.
- Product facts and consumer observations require evidence.
- Compliance fails closed and automatic revision is bounded.
- Human reviewers can approve, edit, or reject a checkpointed draft.
- API routes contain transport logic only; workflows live in services and graph nodes.
- Tests and CI use deterministic providers and require no paid model key.

