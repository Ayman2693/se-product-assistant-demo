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
    description,
    architecture="open",
    antenna="external",
    form_factor=None,
):
    product = Product(
        part_number=pn,
        manufacturer="Test",
        category="Bluetooth LE",
        description=description,
        tags_json="[]",
    )
    db.add(product)
    db.flush()
    db.add(ProductFeature(
        product_id=product.id,
        technologies_json='["bluetooth"]',
        has_bluetooth=True,
        architecture=architecture,
        antenna=antenna,
        form_factor=form_factor,
        imported_live=True,
        raw_features_json="{}",
    ))
    db.flush()
    return product


def _qualified_request(**overrides):
    values = dict(
        product_domain="connectivity",
        technologies=["bluetooth"],
        bluetooth_required=True,
        architecture="open",
        antenna="external",
    )
    values.update(overrides)
    return MatchRequest(**values)


def test_connector_is_asked_when_it_splits_top_bluetooth_tie():
    db = _db()
    for i in range(5):
        _add(
            db,
            f"PIN-{i}",
            description="Bluetooth 5.3 open CPU module with antenna pin 10x12x2mm",
        )
    for i in range(5):
        _add(
            db,
            f"UFL-{i}",
            description="Bluetooth 5.3 open CPU module with U.FL connector 10x12x2mm",
        )
    db.commit()

    result = choose_adaptive_question(db, _qualified_request())

    assert result["question"] is not None
    assert result["question"]["mode"] == "tie_break"
    assert result["question"]["top_tie_count"] == 10
    assert result["question"]["key"] == "antennaConnector"
    assert result["question"]["information_gain"] > 0


def test_connector_answer_reduces_candidates_and_engine_can_continue():
    db = _db()
    # U.FL group differs in footprint; after connector choice, footprint is a
    # useful next discriminator rather than declaring equivalence immediately.
    for i in range(4):
        _add(
            db,
            f"UFL-S-{i}",
            description="Bluetooth 5.3 open CPU module with U.FL connector 8x10x2mm",
        )
    for i in range(4):
        _add(
            db,
            f"UFL-L-{i}",
            description="Bluetooth 5.3 open CPU module with U.FL connector 12x15x2mm",
        )
    for i in range(4):
        _add(
            db,
            f"PIN-{i}",
            description="Bluetooth 5.3 open CPU module with antenna pin 10x12x2mm",
        )
    db.commit()

    result = choose_adaptive_question(
        db,
        _qualified_request(antenna_connector="ufl"),
    )

    assert result["question"] is not None
    assert result["question"]["mode"] == "tie_break"
    assert result["question"]["key"] == "maxFootprint"
    assert result["question"]["top_tie_count"] == 8


def test_optional_no_preference_is_not_asked_again():
    db = _db()
    for i in range(3):
        _add(
            db,
            f"PIN-{i}",
            description="Bluetooth 5.3 open CPU module with antenna pin 10x12x2mm",
        )
    for i in range(3):
        _add(
            db,
            f"UFL-{i}",
            description="Bluetooth 5.3 open CPU module with U.FL connector 10x12x2mm",
        )
    db.commit()

    result = choose_adaptive_question(
        db,
        _qualified_request(answered_open_fields=["antennaConnector"]),
    )

    assert result["question"] is None or result["question"]["key"] != "antennaConnector"


def test_sparse_optional_data_does_not_trigger_interrogation():
    db = _db()
    # Only one of ten candidates exposes a connector signal -> 10% coverage.
    _add(
        db,
        "UFL-0",
        description="Bluetooth 5.3 open CPU module with U.FL connector",
    )
    for i in range(9):
        _add(
            db,
            f"UNKNOWN-{i}",
            description="Bluetooth 5.3 open CPU module",
        )
    db.commit()

    result = choose_adaptive_question(db, _qualified_request())

    assert result["question"] is None


def test_single_top_candidate_skips_optional_tie_questions():
    db = _db()
    _add(
        db,
        "TOP",
        description="Bluetooth 5.3 open CPU module with antenna pin",
    )
    db.commit()

    result = choose_adaptive_question(db, _qualified_request())

    assert result["question"] is None
