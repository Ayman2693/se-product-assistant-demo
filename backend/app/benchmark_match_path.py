"""Synthetic benchmark for the Phase 4.7.5 candidate-loading path.

Run from backend:
    python -m app.benchmark_match_path
"""

from time import perf_counter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductFeature
from app.routers.products import _load_match_candidates
from app.schemas import MatchRequest


def main():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    total = 4306
    wifi_count = 420

    for i in range(total):
        wifi = i < wifi_count
        product = Product(
            part_number=f"P-{i:04d}",
            manufacturer="Synthetic",
            category="Wi-Fi Modules" if wifi else "Other Components",
            description="Wi-Fi 6 module" if wifi else "Other catalog component",
            tags_json='["wifi"]' if wifi else "[]",
        )
        db.add(product)
        db.flush()
        db.add(ProductFeature(
            product_id=product.id,
            technologies_json='["wifi"]' if wifi else "[]",
            wifi_generation="6" if wifi else None,
            raw_features_json="{}",
        ))

    db.commit()

    start = perf_counter()
    rows = _load_match_candidates(
        db,
        MatchRequest(technologies=["wifi"], wifi_generation=["6"]),
    )
    elapsed = (perf_counter() - start) * 1000

    print(f"Catalog products: {total}")
    print(f"SQL candidates:   {len(rows)}")
    print(f"Candidate load:   {elapsed:.2f} ms")


if __name__ == "__main__":
    main()
