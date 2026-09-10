import argparse
import asyncio
import json

from app.db import SessionLocal
from app.services.evidence_service import (
    discover_documents,
    ingest_documents,
    seed_catalog_evidence,
)


def parse_args():
    p = argparse.ArgumentParser(
        description="Build SE Product Assistant evidence and document indexes."
    )
    p.add_argument(
        "--catalog",
        action="store_true",
        help="Create evidence records from the current catalog/structured feature data.",
    )
    p.add_argument(
        "--discover-documents",
        action="store_true",
        help="Visit SE product pages and discover datasheet/manual/document links.",
    )
    p.add_argument(
        "--parse-documents",
        action="store_true",
        help="Download discovered PDFs, extract page text/chunks and create verified evidence.",
    )
    p.add_argument("--product-id", type=int, default=None)
    p.add_argument("--document-id", type=int, default=None)
    p.add_argument("--limit", type=int, default=None)
    return p.parse_args()


async def main():
    args = parse_args()

    if not args.catalog and not args.discover_documents and not args.parse_documents:
        args.catalog = True

    db = SessionLocal()
    try:
        output = {}

        if args.catalog:
            output["catalog"] = seed_catalog_evidence(
                db,
                limit=args.limit,
            )

        if args.discover_documents:
            output["documents"] = await discover_documents(
                db,
                product_id=args.product_id,
                limit=args.limit,
            )

        if args.parse_documents:
            output["parsing"] = await ingest_documents(
                db,
                document_id=args.document_id,
                product_id=args.product_id,
                limit=args.limit,
            )

        print(json.dumps(output, indent=2, ensure_ascii=False))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
