"""Formal database-backed evaluation preflight and pgvector retrieval runner.

Unlike the legacy v2 component set, this module refuses to score lexical
retrieval, synthetic rows, or a database with missing embeddings as formal RAG.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from beauty_creator_agent.db.models import ConsumerReview, ContentExample, Product
from beauty_creator_agent.rag.embeddings import EmbeddingProvider
from beauty_creator_agent.schemas.common import ContractModel, NonEmptyStr
from beauty_creator_agent.tools.contracts import SemanticSearchQuery
from beauty_creator_agent.tools.database_catalog import DatabaseCatalogTools

RetrieverType = Literal["product", "review", "content"]
RETRIEVER_TYPES: tuple[RetrieverType, ...] = ("product", "review", "content")
FORMAL_COHORT_COUNTS = {
    "routing": 25,
    "retrieval": 25,
    "generation": 15,
    "compliance": 15,
}
FORMAL_TOTAL_CASES = sum(FORMAL_COHORT_COUNTS.values())
BASELINE_CONFIGURATIONS = ("single_llm", "llm_plus_rag", "full_rag_agent")


class BaselineConfiguration(ContractModel):
    """Comparable component switches for a future formal evaluation run."""

    name: Literal["single_llm", "llm_plus_rag", "full_rag_agent"]
    uses_retrieval: bool
    uses_evidence_context: bool
    uses_claim_verification: bool
    uses_rule_engine: bool
    uses_semantic_review: bool
    uses_revision_loop: bool
    exposes_human_review_boundary: bool


FORMAL_BASELINES: tuple[BaselineConfiguration, ...] = (
    BaselineConfiguration(
        name="single_llm",
        uses_retrieval=False,
        uses_evidence_context=False,
        uses_claim_verification=False,
        uses_rule_engine=False,
        uses_semantic_review=False,
        uses_revision_loop=False,
        exposes_human_review_boundary=False,
    ),
    BaselineConfiguration(
        name="llm_plus_rag",
        uses_retrieval=True,
        uses_evidence_context=True,
        uses_claim_verification=False,
        uses_rule_engine=False,
        uses_semantic_review=False,
        uses_revision_loop=False,
        exposes_human_review_boundary=False,
    ),
    BaselineConfiguration(
        name="full_rag_agent",
        uses_retrieval=True,
        uses_evidence_context=True,
        uses_claim_verification=True,
        uses_rule_engine=True,
        uses_semantic_review=True,
        uses_revision_loop=True,
        exposes_human_review_boundary=True,
    ),
)


def _default_filters() -> SemanticSearchQuery:
    return SemanticSearchQuery(query="placeholder")


class FormalRetrievalCase(ContractModel):
    """A labeled pgvector case. Gold IDs must exist in the imported corpus."""

    id: NonEmptyStr
    kind: Literal["retrieval"]
    retriever: RetrieverType
    query: NonEmptyStr
    filters: SemanticSearchQuery = Field(default_factory=_default_filters)
    gold_source_ids: list[NonEmptyStr] = Field(min_length=1)

    @model_validator(mode="after")
    def query_matches_filters(self) -> "FormalRetrievalCase":
        if self.filters.query != "placeholder" and self.filters.query != self.query:
            raise ValueError("filters.query must match the case query when supplied")
        self.filters.query = self.query
        self.filters.limit = 5
        return self


class FormalRoutingCase(ContractModel):
    """Frozen planner case; the route is evaluated only during a formal run."""

    id: NonEmptyStr
    kind: Literal["routing"]
    query: NonEmptyStr
    gold_route: NonEmptyStr
    metadata: dict[str, Any] = Field(default_factory=dict)
    expected_workflow: list[NonEmptyStr] = Field(default_factory=list)


class FormalGenerationCase(ContractModel):
    """Evidence-backed generation case with independent claim labels."""

    id: NonEmptyStr
    kind: Literal["generation"]
    request: dict[str, Any]
    evidence_source_ids: list[NonEmptyStr] = Field(min_length=1)
    gold_claims: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FormalComplianceCase(ContractModel):
    """Risk-screening case; labels may contain several risks per draft."""

    id: NonEmptyStr
    kind: Literal["compliance"]
    market: NonEmptyStr
    text: NonEmptyStr
    gold_risk_labels: list[NonEmptyStr] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


FormalCase = FormalRoutingCase | FormalRetrievalCase | FormalGenerationCase | FormalComplianceCase


class FormalDataset(ContractModel):
    """Validated, frozen 80-case formal dataset manifest."""

    cases: list[FormalCase]
    sha256: NonEmptyStr

    @property
    def cohort_counts(self) -> dict[str, int]:
        return dict(Counter(case.kind for case in self.cases))


class FormalReport(ContractModel):
    """Report shape reserved for a future measured formal evaluation."""

    evaluation_type: Literal["formal_rag_agent_v3"] = "formal_rag_agent_v3"
    dataset_version: NonEmptyStr
    dataset_sha256: NonEmptyStr
    provider: NonEmptyStr | None = None
    model: NonEmptyStr | None = None
    timestamp_utc: NonEmptyStr | None = None
    total_cases: int = FORMAL_TOTAL_CASES
    routing_cases: int = FORMAL_COHORT_COUNTS["routing"]
    retrieval_cases: int = FORMAL_COHORT_COUNTS["retrieval"]
    generation_cases: int = FORMAL_COHORT_COUNTS["generation"]
    compliance_cases: int = FORMAL_COHORT_COUNTS["compliance"]
    routing_correct: int | None = None
    routing_total: int | None = None
    routing_accuracy: float | None = None
    retrieval_hit_at_5: int | None = None
    retrieval_total: int | None = None
    rag_recall_at_5: float | None = None
    product_hit_at_5: int | None = None
    product_total: int | None = None
    product_recall_at_5: float | None = None
    review_hit_at_5: int | None = None
    review_total: int | None = None
    review_recall_at_5: float | None = None
    content_hit_at_5: int | None = None
    content_total: int | None = None
    content_recall_at_5: float | None = None
    grounded_substantive_claims: int | None = None
    total_substantive_claims: int | None = None
    grounded_claim_rate: float | None = None
    compliance_true_positive: int | None = None
    compliance_false_negative: int | None = None
    compliance_false_positive: int | None = None
    compliance_true_negative: int | None = None
    compliance_recall: float | None = None
    compliance_precision: float | None = None
    compliance_specificity: float | None = None
    failed_model_calls: int = 0
    failed_retrieval_calls: int = 0
    measurement_complete: bool = False
    whole_draft_grounding_measured: bool = False
    per_case_results: list[dict[str, Any]] = Field(default_factory=list)


class FormalDatasetError(RuntimeError):
    """Raised when a formal run cannot honestly be measured."""


def load_retrieval_cases(dataset: Path) -> tuple[list[FormalRetrievalCase], str]:
    content = dataset.read_bytes()
    rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
    cases = [
        FormalRetrievalCase.model_validate(row) for row in rows if row.get("kind") == "retrieval"
    ]
    if not cases:
        raise FormalDatasetError("formal dataset contains no retrieval cases")
    if len({case.id for case in cases}) != len(cases):
        raise FormalDatasetError("formal dataset contains duplicate case IDs")
    kinds = Counter(case.retriever for case in cases)
    if any(kinds[kind] == 0 for kind in RETRIEVER_TYPES):
        raise FormalDatasetError("formal dataset must cover product, review, and content retrieval")
    return cases, hashlib.sha256(content).hexdigest()


def load_formal_dataset(dataset: Path) -> FormalDataset:
    """Load the frozen 25/25/15/15 schema without executing any evaluation."""
    content = dataset.read_bytes()
    rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
    cases: list[FormalCase] = []
    for row in rows:
        kind = row.get("kind")
        if kind == "routing":
            cases.append(FormalRoutingCase.model_validate(row))
        elif kind == "retrieval":
            cases.append(FormalRetrievalCase.model_validate(row))
        elif kind == "generation":
            cases.append(FormalGenerationCase.model_validate(row))
        elif kind == "compliance":
            cases.append(FormalComplianceCase.model_validate(row))
        else:
            raise FormalDatasetError(f"unknown formal cohort: {kind!r}")
    if len({case.id for case in cases}) != len(cases):
        raise FormalDatasetError("formal dataset contains duplicate case IDs")
    counts = Counter(case.kind for case in cases)
    if dict(counts) != FORMAL_COHORT_COUNTS:
        raise FormalDatasetError(
            "formal dataset must contain routing=25, retrieval=25, generation=15, compliance=15"
        )
    retrieval_types = Counter(
        case.retriever for case in cases if isinstance(case, FormalRetrievalCase)
    )
    if any(retrieval_types[kind] == 0 for kind in RETRIEVER_TYPES):
        raise FormalDatasetError("formal retrieval cohort must cover product, review, and content")
    return FormalDataset(cases=cases, sha256=hashlib.sha256(content).hexdigest())


def ratio(numerator: int, denominator: int) -> float | None:
    """Metric helper; zero substantive claims deliberately yields ``None``."""
    return round(numerator / denominator, 4) if denominator else None


def grounding_rate(
    grounded_substantive_claims: int, total_substantive_claims: int
) -> float | None:
    return ratio(grounded_substantive_claims, total_substantive_claims)


def build_unmeasured_report(dataset: FormalDataset, dataset_version: str) -> FormalReport:
    """Create a schema-valid preparation report without claiming a measurement."""
    return FormalReport(dataset_version=dataset_version, dataset_sha256=dataset.sha256)


def _entity_for(kind: RetrieverType) -> type[Product] | type[ConsumerReview] | type[ContentExample]:
    if kind == "product":
        return Product
    if kind == "review":
        return ConsumerReview
    return ContentExample


def preflight_database(
    factory: sessionmaker[Session], cases: list[FormalRetrievalCase]
) -> dict[str, int]:
    """Verify required real corpus coverage before any metric is emitted."""
    counts: dict[str, int] = {}
    with factory() as session:
        for kind in RETRIEVER_TYPES:
            entity = _entity_for(kind)
            total = session.scalar(
                select(func.count()).select_from(entity).where(entity.source != "sample")
            )
            embedded = session.scalar(
                select(func.count())
                .select_from(entity)
                .where(entity.source != "sample", entity.embedding.is_not(None))
            )
            counts[f"{kind}_rows"] = int(total or 0)
            counts[f"{kind}_embedded_rows"] = int(embedded or 0)
            if not total or not embedded:
                raise FormalDatasetError(
                    f"formal pgvector evaluation blocked: {kind} corpus has no real embedded rows"
                )
        for case in cases:
            entity = _entity_for(case.retriever)
            existing = set(
                session.scalars(
                    select(entity.source_id).where(entity.source_id.in_(case.gold_source_ids))
                ).all()
            )
            missing = set(case.gold_source_ids) - existing
            if missing:
                raise FormalDatasetError(
                    f"missing gold source IDs for {case.id}: {sorted(missing)}"
                )
    return counts


async def run_retrieval(
    cases: list[FormalRetrievalCase],
    catalog: DatabaseCatalogTools,
    embeddings: EmbeddingProvider,
) -> dict[str, Any]:
    """Execute the three actual pgvector retrievers and calculate Recall@5."""
    results: list[dict[str, Any]] = []
    by_type: dict[str, dict[str, int]] = {
        kind: {"hits": 0, "total": 0, "failed": 0} for kind in RETRIEVER_TYPES
    }
    for case in cases:
        bucket = by_type[case.retriever]
        bucket["total"] += 1
        try:
            vector = await embeddings.embed_query(case.query)
            result = {
                "product": catalog.semantic_search_products,
                "review": catalog.semantic_search_reviews,
                "content": catalog.semantic_search_content,
            }[case.retriever](case.filters, vector)
            hit = bool(set(case.gold_source_ids) & set(result.source_ids))
            bucket["hits"] += hit
            results.append(
                {
                    "id": case.id,
                    "retriever": case.retriever,
                    "hit_at_5": hit,
                    "gold_source_ids": case.gold_source_ids,
                    "retrieved_source_ids": result.source_ids,
                }
            )
        except Exception as exc:
            bucket["failed"] += 1
            results.append(
                {"id": case.id, "retriever": case.retriever, "error_type": type(exc).__name__}
            )
    total = sum(bucket["total"] for bucket in by_type.values())
    hits = sum(bucket["hits"] for bucket in by_type.values())
    failed = sum(bucket["failed"] for bucket in by_type.values())
    return {
        "metric": "pgvector_semantic_recall_at_5",
        "numerator": hits,
        "denominator": total,
        "percentage": round(hits / total, 4) if total else None,
        "failed_retrieval_calls": failed,
        "by_retriever": by_type,
        "cases": results,
    }
