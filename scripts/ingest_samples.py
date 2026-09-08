import argparse
from pathlib import Path

from beauty_creator_agent.db.repositories.catalog import (
    ContentRepository,
    ProductRepository,
    ReviewRepository,
)
from beauty_creator_agent.db.session import create_db_engine, create_session_factory, session_scope
from beauty_creator_agent.schemas.ingestion import NormalizedContent, NormalizedReview
from beauty_creator_agent.services.ingestion import (
    deduplicate,
    load_raw_jsonl,
    normalize_sample_product,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Idempotently ingest bundled JSONL data")
    parser.add_argument("--data-dir", type=Path, default=Path("data/samples"))
    args = parser.parse_args()

    products = deduplicate(
        normalize_sample_product(row) for row in load_raw_jsonl(args.data_dir / "products.jsonl")
    )
    real_products_path = Path("data/openbeautyfacts/products.jsonl")
    if real_products_path.exists():
        real_products = [
            normalize_sample_product(row) for row in load_raw_jsonl(real_products_path)
        ]
        products = deduplicate([*products, *real_products])
    reviews = deduplicate(
        NormalizedReview.model_validate({key: value for key, value in row.items() if key != "id"})
        for row in load_raw_jsonl(args.data_dir / "reviews.jsonl")
    )
    content = deduplicate(
        NormalizedContent.model_validate({key: value for key, value in row.items() if key != "id"})
        for row in load_raw_jsonl(args.data_dir / "content_examples.jsonl")
    )

    factory = create_session_factory(create_db_engine())
    with session_scope(factory) as session:
        product_repo = ProductRepository(session)
        review_repo = ReviewRepository(session)
        content_repo = ContentRepository(session)
        for record in products:
            product_repo.upsert(record.model_dump())
        for record in reviews:
            review_repo.upsert(record.model_dump())
        for record in content:
            content_repo.upsert(record.model_dump())
    print(
        f"Ingested {len(products)} products, {len(reviews)} reviews, "
        f"{len(content)} content examples"
    )


if __name__ == "__main__":
    main()
