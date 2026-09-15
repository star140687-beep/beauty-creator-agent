"""Import a bounded or full local Sephora dataset into PostgreSQL in batches."""

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from beauty_creator_agent.db.models import ConsumerReview, Product
from beauty_creator_agent.db.session import create_db_engine, create_session_factory
from beauty_creator_agent.services.bulk_import import import_rows
from beauty_creator_agent.services.sephora_data import products, reviews


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream a local Sephora dataset into PostgreSQL")
    parser.add_argument("--products", type=Path, required=True, help="Local product_info.csv")
    parser.add_argument("--reviews", type=Path, required=True, help="Local Skincare Reviews.csv")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--limit-reviews", type=int, default=2000)
    parser.add_argument(
        "--all-reviews", action="store_true", help="Explicitly import every valid review"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate and count without database writes"
    )
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 5000:
        parser.error("--batch-size must be between 1 and 5000")
    if args.limit_reviews < 1:
        parser.error("--limit-reviews must be positive")
    for path in (args.products, args.reviews):
        if not path.is_file():
            parser.error(f"source file not found: {path}")

    limit = None if args.all_reviews else args.limit_reviews
    session: Session | None = None
    engine = None
    if not args.dry_run:
        engine = create_db_engine()
        session = create_session_factory(engine)()
    try:
        product_count = import_rows(
            session, Product, products(args.products), batch_size=args.batch_size, limit=None
        )
        review_count = import_rows(
            session, ConsumerReview, reviews(args.reviews), batch_size=args.batch_size, limit=limit
        )
    finally:
        if session is not None:
            session.close()
        if engine is not None:
            engine.dispose()
    mode = "validated" if args.dry_run else "upserted"
    print(f"{mode} {product_count} products and {review_count} reviews")


if __name__ == "__main__":
    main()
