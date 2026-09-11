from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.adaptive_questions import choose_adaptive_question


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _add(
    db,
    pn,
    *,
    category="Wi-Fi Modules",
    technologies=None,
    wifi_generation=None,
    architecture=None,
    antenna=None,
    raw_features_json="{}",
):
    product = Product(
        part_number=pn,
        manufacturer="Test",
        category=category,
        description="test",
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
        wifi_generation=wifi_generation,
        architecture=architecture,
        antenna=antenna,
        raw_features_json=raw_features_json,
    ))


def test_adaptive_engine_prefers_field_that_actually_splits_candidates():
    db = _db()
    # Wi-Fi generation is identical for every product, while architecture
    # creates a balanced split. The engine should ask architecture first.
    for i in range(8):
        _add(
            db,
            f"W{i}",
            technologies=["wifi"],
            wifi_generation="6",
            architecture="open" if i < 4 else "host",
        )
    db.commit()

    result = choose_adaptive_question(
        db,
        MatchRequest(product_domain="connectivity", technologies=["wifi"]),
    )

    assert result["candidate_count"] == 8
    assert result["question"]["key"] == "architecture"
    assert result["question"]["information_gain"] > 0


def test_required_question_is_still_asked_when_catalog_cannot_discriminate_it():
    db = _db()
    for i in range(5):
        _add(
            db,
            f"W{i}",
            technologies=["wifi"],
            wifi_generation="6",
            architecture="host",
        )
    db.commit()

    result = choose_adaptive_question(
        db,
        MatchRequest(
            product_domain="connectivity",
            technologies=["wifi"],
            architecture="host",
        ),
    )

    # Generation is a core qualification field. It remains askable even if
    # every current product happens to expose the same value.
    assert result["question"]["key"] == "wifiGeneration"
    assert result["question"]["required"] is True


def test_capacitor_numeric_options_are_derived_from_remaining_catalog_values():
    db = _db()
    for i, capacitance in enumerate([1, 10, 47, 100]):
        _add(
            db,
            f"C{i}",
            category="Capacitors",
            raw_features_json=(
                '{"capacitance_uf": %s, "capacitor_voltage_v": 25, '
                '"capacitor_technology": "Ceramic", '
                '"capacitor_mounting": "SMD", '
                '"capacitor_tolerance_pct": 10}'
            ) % capacitance,
        )
    db.commit()

    result = choose_adaptive_question(
        db,
        MatchRequest(
            product_domain="components",
            catalog_category="Capacitors",
        ),
    )

    assert result["question"]["key"] == "capacitorCapacitance"
    labels = {option["label"] for option in result["question"]["options"]}
    assert "47 µF" in labels


def test_answered_field_is_not_asked_again():
    db = _db()
    for i in range(6):
        _add(
            db,
            f"W{i}",
            technologies=["wifi"],
            wifi_generation="5" if i < 3 else "6",
            architecture="open" if i % 2 else "host",
        )
    db.commit()

    result = choose_adaptive_question(
        db,
        MatchRequest(
            product_domain="connectivity",
            technologies=["wifi"],
            architecture="host",
            wifi_generation=["5", "6"],
        ),
    )

    # No unanswered required Wi-Fi fields remain.
    assert result["question"] is None
