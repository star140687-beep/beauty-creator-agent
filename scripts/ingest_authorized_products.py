"""Import authorized product records for any brand from private local JSONL."""

import argparse
from pathlib import Path

from beauty_creator_agent.db.models import Product
from beauty_creator_agent.db.session import create_db_engine, create_session_factory
from beauty_creator_agent.services.authorized_products import product_rows
from beauty_creator_agent.services.bulk_import import import_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Import rights-cleared multi-brand products")
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--manufacturer-documented", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error(f"source file not found: {args.source}")
    if not 1 <= args.batch_size <= 5000:
        parser.error("--batch-size must be between 1 and 5000")
    if args.source_name == "sample":
        parser.error("authorized products must not be marked sample")
    engine = None if args.dry_run else create_db_engine()
    session = None if engine is None else create_session_factory(engine)()
    try:
        count = import_rows(
            session,
            Product,
            product_rows(
                args.source,
                source_name=args.source_name,
                license_name=args.license,
                manufacturer_documented=args.manufacturer_documented,
            ),
            batch_size=args.batch_size,
            limit=None,
        )
    finally:
        if session is not None:
            session.close()
        if engine is not None:
            engine.dispose()
    print(f"{'validated' if args.dry_run else 'upserted'} {count} product records")


if __name__ == "__main__":
    main()
