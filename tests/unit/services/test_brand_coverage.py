from beauty_creator_agent.services.brand_coverage import summarize_brands


def test_brand_coverage_contains_only_aggregate_counts() -> None:
    report = summarize_brands(
        [{"brand": "Brand A", "description": "Private text"}],
        [{"brand": "Brand A", "review_text": "Personal review"}],
    )

    assert report["product_brands"] == 1
    assert report["review_brands"] == 1
    assert report["brands"] == [
        {"brand": "Brand A", "product_records": 1, "review_records": 1}
    ]
    assert "Personal review" not in str(report)
