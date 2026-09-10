import asyncio
import json

from app.db import Base, engine, SessionLocal
from app.models import Product
from app.seed import seed
from app.services.catalog_importer import import_catalog
from app.services.evidence_service import seed_catalog_evidence

MIN_FULL_CATALOG_PRODUCTS = 1500


async def bootstrap():
    Base.metadata.create_all(bind=engine)
    seed()

    db = SessionLocal()
    try:
        before = db.query(Product).count()
        print(f"[bootstrap] products before live import: {before}", flush=True)

        if before < MIN_FULL_CATALOG_PRODUCTS:
            result = await import_catalog(db)
            print(json.dumps({"catalog_import": result}, indent=2, ensure_ascii=False), flush=True)
        else:
            print("[bootstrap] full catalog already present; skipping live import.", flush=True)

        evidence_result = seed_catalog_evidence(db)
        after = db.query(Product).count()
        print(
            json.dumps(
                {"products_after": after, "evidence": evidence_result},
                indent=2,
                ensure_ascii=False,
            ),
            flush=True,
        )
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(bootstrap())
