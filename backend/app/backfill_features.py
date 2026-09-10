import json
from app.db import Base, engine, SessionLocal
from app.models import Product, ProductFeature
from app.services.feature_extractor import extract_features, feature_values_for_model

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = 0
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
            count += 1
        db.commit()
        print(f"Structured features generated for {count} products.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
