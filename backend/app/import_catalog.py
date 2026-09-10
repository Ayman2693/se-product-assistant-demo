import argparse
import asyncio

from app.db import Base, engine, SessionLocal
from app.services.catalog_importer import import_catalog

def main():
    parser = argparse.ArgumentParser(description="Import SE product catalog into the local database.")
    parser.add_argument("--source", help="Import only matching source/category, e.g. LTE or Bluetooth")
    parser.add_argument("--limit-sources", type=int, help="Only import the first N matching catalog sections")
    parser.add_argument("--max-pages", type=int, help="Limit pagination per catalog section for testing")
    parser.add_argument("--all", action="store_true", help="Import all configured SE catalog sections")
    args = parser.parse_args()

    if not args.all and not args.source and args.limit_sources is None:
        # Safe first run: one source, one page.
        args.limit_sources = 1
        args.max_pages = args.max_pages or 1
        print("No scope supplied: running a safe test import (1 source / 1 page).")
        print("Use --all for the complete configured catalog.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = asyncio.run(import_catalog(
            db,
            source_filter=args.source,
            limit_sources=args.limit_sources,
            max_pages=args.max_pages,
        ))
        print()
        print("Catalog import complete")
        print("-----------------------")
        print(f"Sources requested : {result['sources_requested']}")
        print(f"Sources succeeded : {result['sources_succeeded']}")
        print(f"Products seen     : {result['products_seen']}")
        if result["failed"]:
            print("Failures:")
            for row in result["failed"]:
                print(f" - {row['source']}: {row['error']}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
