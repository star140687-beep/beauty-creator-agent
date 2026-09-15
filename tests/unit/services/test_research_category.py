import pytest

from beauty_creator_agent.schemas.planner import PlannerDecision
from beauty_creator_agent.schemas.task import TaskCreate
from beauty_creator_agent.services.research import ResearchService, sample_catalog
from beauty_creator_agent.tools.catalog import CatalogTools


@pytest.mark.asyncio
async def test_content_research_uses_product_category_not_product_name() -> None:
    catalog = CatalogTools(
        products=[
            {
                "source_id": "product:1",
                "source": "owned",
                "brand": "Example",
                "product_name": "Hydrating Serum",
                "category": "serum",
                "description": "An owned product record.",
            }
        ],
        reviews=[],
        content=[
            {
                "source_id": "content:1",
                "source": "owned",
                "platform": "xiaohongshu",
                "category": "serum",
                "title": "Serum guide",
                "body": "A category-level content pattern.",
            }
        ],
    )
    request = TaskCreate.model_validate(
        {
            "product": {"name": "Hydrating Serum"},
            "platform": "xiaohongshu",
            "objective": "Write a guide",
        }
    )
    plan = PlannerDecision.model_validate(
        {
            "intent": "generate",
            "platform": "xiaohongshu",
            "needs_product_research": False,
            "needs_consumer_research": False,
            "needs_content_research": True,
            "needs_trend_research": False,
            "needs_writer": True,
            "needs_compliance": True,
            "reasoning_summary": "A category pattern is useful.",
        }
    )

    evidence = await ResearchService(catalog).research({"request": request, "plan": plan})

    assert any(item.source_id == "content:1" for item in evidence)
    assert not any(item.source_id == "product:1" for item in evidence)


def test_openbeautyfacts_provenance_survives_sample_catalog_research() -> None:
    row = next(
        row for row in sample_catalog().products if row["source"] == "open_beauty_facts"
    )

    evidence = ResearchService._to_evidence([row], "product_fact", "external_search")

    assert evidence[0].metadata["license"] == "ODbL-1.0"
    assert evidence[0].metadata["source_url"].startswith("https://")
