import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from beauty_creator_agent.core.config import get_settings
from beauty_creator_agent.db.session import create_db_engine, create_session_factory
from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.evidence import EvidenceItem
from beauty_creator_agent.tools.catalog import CatalogTools
from beauty_creator_agent.tools.contracts import ContentSearchQuery, SearchQuery
from beauty_creator_agent.tools.database_catalog import DatabaseCatalogTools


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sample_catalog(data_dir: Path = Path("data/samples")) -> CatalogTools:
    product_rows = _rows(data_dir / "products.jsonl")
    real_products = Path("data/openbeautyfacts/products.jsonl")
    if real_products.exists():
        for row in _rows(real_products):
            row["source_metadata"] = {
                "source_url": row.get("source_url"),
                "license": row.get("license"),
                "barcode": row.get("barcode"),
                "retrieved_at": row.get("retrieved_at"),
                "verification": "crowdsourced_unverified",
            }
            product_rows.append(row)
    return CatalogTools(
        products=product_rows,
        reviews=_rows(data_dir / "reviews.jsonl"),
        content=_rows(data_dir / "content_examples.jsonl"),
    )


@lru_cache(maxsize=1)
def _database_factory() -> sessionmaker[Session]:
    return create_session_factory(create_db_engine())


def configured_catalog() -> CatalogTools | DatabaseCatalogTools:
    if get_settings().research_backend == "database":
        return DatabaseCatalogTools(_database_factory())
    return sample_catalog()


class ResearchService:
    """Collect evidence exclusively through user input and typed catalog tools."""

    def __init__(self, tools: CatalogTools | DatabaseCatalogTools) -> None:
        self.tools = tools

    async def research(self, state: MarketingState) -> list[EvidenceItem]:
        request = state["request"]
        plan = state["plan"]
        evidence = [
            EvidenceItem(
                id="user_product_name",
                evidence_type="product_fact",
                source_type="user_input",
                source_id="user_product_input",
                content=f"产品名称：{request.product.name}",
                reliability="high",
            )
        ]
        if request.product.description:
            evidence.append(
                EvidenceItem(
                    id="user_product_description",
                    evidence_type="product_fact",
                    source_type="user_input",
                    source_id="user_product_description",
                    content=request.product.description,
                    reliability="medium",
                )
            )
        for reference in request.uploaded_references:
            if reference.role != "product_material":
                continue
            evidence.append(
                EvidenceItem(
                    id=reference.source_id,
                    evidence_type="product_fact",
                    source_type="user_input",
                    source_id=reference.source_id,
                    content=reference.content,
                    reliability="medium",
                    metadata={
                        "upload_role": reference.role,
                        "media_type": reference.media_type,
                        "sha256": reference.sha256,
                        "size_bytes": reference.size_bytes,
                    },
                )
            )
        query = request.product.name
        product_rows: list[dict[str, Any]] = []
        if plan.needs_product_research or plan.needs_content_research:
            result = self.tools.search_product_knowledge(SearchQuery(query=query))
            product_rows = result.data or []
            if plan.needs_product_research:
                evidence.extend(self._to_evidence(product_rows, "product_fact", "external_search"))
        if plan.needs_consumer_research:
            result = self.tools.search_consumer_reviews(SearchQuery(query=query))
            evidence.extend(
                self._to_evidence(result.data or [], "consumer_review", "consumer_dataset")
            )
        if plan.needs_content_research:
            category = query
            for row in product_rows:
                candidate = row.get("category")
                if isinstance(candidate, str) and candidate.strip():
                    category = candidate
                    break
            result = self.tools.search_content_examples(
                ContentSearchQuery(query=category, platform=request.platform)
            )
            evidence.extend(
                self._to_evidence(result.data or [], "content_pattern", "content_dataset")
            )
        return evidence

    @staticmethod
    def _to_evidence(
        rows: list[dict[str, Any]], evidence_type: str, source_type: str
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for row in rows:
            content = row.get("description") or row.get("review_text") or row.get("body") or ""
            items.append(
                EvidenceItem.model_validate(
                    {
                        "id": f"evidence_{row['source_id']}",
                        "evidence_type": evidence_type,
                        "source_type": source_type,
                        "source_id": row["source_id"],
                        "content": content,
                        "reliability": "medium",
                        "metadata": {
                            "category": row.get("category"),
                            "source": row.get("source"),
                            "license": (row.get("source_metadata") or {}).get("license"),
                            "dataset_url": (row.get("source_metadata") or {}).get("dataset_url"),
                            "source_url": (row.get("source_metadata") or {}).get("source_url"),
                        },
                    }
                )
            )
            source_metadata = row.get("source_metadata") or {}
            if (
                evidence_type == "product_fact"
                and source_metadata.get("verification")
                == "operator_confirmed_manufacturer_documented"
            ):
                claim_evidence = source_metadata.get("claim_evidence") or {}
                for claim in row.get("claims") or []:
                    evidence_url = claim_evidence.get(claim)
                    if not evidence_url:
                        continue
                    digest = hashlib.sha256(claim.encode("utf-8")).hexdigest()[:16]
                    items.append(
                        EvidenceItem(
                            id=f"evidence_{row['source_id']}_claim_{digest}",
                            evidence_type="product_fact",
                            source_type="official",
                            source_id=f"{row['source_id']}:claim:{digest}",
                            content=claim,
                            reliability="high",
                            metadata={
                                "brand": row.get("brand"),
                                "evidence_url": evidence_url,
                                "verification": source_metadata.get("verification"),
                            },
                        )
                    )
        return items
