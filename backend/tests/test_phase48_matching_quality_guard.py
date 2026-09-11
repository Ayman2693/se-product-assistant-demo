from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.matching_engine import compare_fast_vs_exhaustive


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _add(db, pn, category, description="", technologies=None, **features):
    product = Product(
        part_number=pn,
        manufacturer="Test",
        category=category,
        description=description,
        tags_json="[]",
    )
    db.add(product)
    db.flush()
    db.add(ProductFeature(
        product_id=product.id,
        technologies_json=(
            '["' + '","'.join(technologies or []) + '"]'
            if technologies else "[]"
        ),
        raw_features_json=features.pop("raw_features_json", "{}"),
        **features,
    ))
    return product


def test_fast_path_matches_exhaustive_for_singular_plural_category():
    db = _db()
    _add(db, "C1", "Capacitor", raw_features_json='{"capacitance_uf":47}')
    _add(db, "C2", "Capacitors", raw_features_json='{"capacitance_uf":100}')
    _add(db, "W1", "Wi-Fi Modules", technologies=["wifi"], wifi_generation="6")
    db.commit()

    result = compare_fast_vs_exhaustive(
        db,
        MatchRequest(catalog_category="Capacitors"),
    )
    assert result["ok"]
    assert result["fast_matches"] == result["exhaustive_matches"] == 2


def test_fast_path_recalls_ble_wording_without_structured_features():
    db = _db()
    _add(db, "B1", "BLE Modules", description="Low power BLE module")
    _add(db, "B2", "Bluetooth Modules", technologies=["bluetooth"], has_bluetooth=True)
    _add(db, "S1", "Pressure Sensors")
    db.commit()

    result = compare_fast_vs_exhaustive(
        db,
        MatchRequest(technologies=["bluetooth"]),
    )
    assert result["ok"]
    assert result["fast_matches"] == result["exhaustive_matches"] == 2


def test_quality_guard_compares_top_cutoff_pool_not_just_count():
    db = _db()
    for i in range(15):
        _add(
            db,
            f"W{i}",
            "Wi-Fi Modules",
            technologies=["wifi"],
            wifi_generation="6",
        )
    db.commit()

    result = compare_fast_vs_exhaustive(
        db,
        MatchRequest(technologies=["wifi"], wifi_generation=["6"]),
        limit=10,
    )
    assert result["ok"]
    assert result["fast_top_cutoff_ids"] == result["exhaustive_top_cutoff_ids"]
