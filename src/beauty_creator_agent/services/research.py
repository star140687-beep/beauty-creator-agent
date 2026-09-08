import json
from pathlib import Path
from typing import Any

from beauty_creator_agent.graph.state import MarketingState
from beauty_creator_agent.schemas.evidence import EvidenceItem
from beauty_creator_agent.tools.catalog import CatalogTools
from beauty_creator_agent.tools.contracts import ContentSearchQuery, SearchQuery


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sample_catalog(data_dir: Path = Path("data/samples")) -> CatalogTools:
    product_rows = _rows(data_dir / "products.jsonl")
    real_products = Path("data/openbeautyfacts/products.jsonl")
    if real_products.exists():
        product_rows.extend(_rows(real_products))
    return CatalogTools(
        products=product_rows,
        reviews=_rows(data_dir / "reviews.jsonl"),
        content=_rows(data_dir / "content_examples.jsonl"),
    )


class ResearchService:
    """Collect evidence exclusively through user input and typed catalog tools."""

    def __init__(self, tools: CatalogTools) -> None:
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
        query = " ".join(filter(None, [request.product.brand, request.product.name]))
        if plan.needs_product_research:
            result = self.tools.search_product_knowledge(SearchQuery(query=query))
            evidence.extend(self._to_evidence(result.data or [], "product_fact", "external_search"))
        if plan.needs_consumer_research:
            result = self.tools.search_consumer_reviews(SearchQuery(query=query))
            evidence.extend(
                self._to_evidence(result.data or [], "consumer_review", "consumer_dataset")
            )
        if plan.needs_content_research:
            result = self.tools.search_content_examples(
                ContentSearchQuery(query=request.product.name, platform=request.platform)
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
                        "metadata": {"category": row.get("category")},
                    }
                )
            )
        return items
