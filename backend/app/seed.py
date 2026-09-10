import json
from pathlib import Path
from app.db import Base, engine, SessionLocal
from app.models import Product, ProductFeature
from app.services.feature_extractor import extract_features, feature_values_for_model

DATA = Path(__file__).resolve().parents[1] / "data" / "products_seed.json"

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rows = json.loads(DATA.read_text(encoding="utf-8"))
        for item in rows:
            part_number = item.get("id")
            if not part_number:
                continue
            existing = db.query(Product).filter(Product.part_number == part_number).first()
            values = dict(
                part_number=part_number,
                manufacturer=item.get("manufacturer", "Unknown"),
                category=item.get("category", ""),
                description=item.get("desc", ""),
                tags_json=json.dumps(item.get("tags", []), ensure_ascii=False),
                product_url=item.get("url", ""),
                lifecycle=item.get("lifecycle", "Not verified"),
                availability=item.get("availability", "Check live SE page"),
                exact=bool(item.get("exact", False)),
            )
            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
            else:
                db.add(Product(**values))
        db.flush()
        for product in db.query(Product).all():
            try:
                tags = json.loads(product.tags_json or "[]")
            except Exception:
                tags = []
            extracted = extract_features(
                product.part_number,
                product.manufacturer,
                product.category,
                product.description,
                tags,
            )
            feature = product.features
            if feature is None:
                feature = ProductFeature(product=product)
                db.add(feature)
            for key, value in feature_values_for_model(extracted).items():
                setattr(feature, key, value)
            feature.source_category = product.category
            feature.source_url = product.product_url
        db.commit()
        print(f"Seeded {db.query(Product).count()} products with structured features.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
