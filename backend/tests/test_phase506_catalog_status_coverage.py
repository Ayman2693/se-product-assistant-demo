from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductFeature
from app.routers.products import catalog_status


def test_catalog_status_reports_category_counts_and_zero_categories():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    product = Product(
        part_number="TEST-CRYSTAL",
        manufacturer="Test",
        category="Crystals",
        description="test",
        tags_json="[]",
        product_url="",
        lifecycle="",
        availability="",
        exact=True,
    )
    db.add(product)
    db.flush()
    db.add(ProductFeature(product_id=product.id, imported_live=True, technologies_json='["timing"]'))
    db.commit()

    result = catalog_status(db)

    assert result["category_counts"]["Crystals"] == 1
    assert "Crystals" not in result["zero_categories"]
    assert "Timing IC" in result["zero_categories"]
