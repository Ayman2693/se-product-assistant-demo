from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.adaptive_questions import choose_adaptive_question
from app.services.evidence_matcher import evidence_sort_key
from app.services.matcher import score_product


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _add(
    db,
    pn,
    *,
    category="Bluetooth LE",
    description="",
    technologies=None,
    has_bluetooth=True,
    wifi_generation=None,
    architecture=None,
    antenna=None,
):
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
        has_bluetooth=has_bluetooth,
        wifi_generation=wifi_generation,
        architecture=architecture,
        antenna=antenna,
        imported_live=True,
        raw_features_json="{}",
    ))
    db.flush()
    return product


def test_bluetooth_capability_is_not_scored_twice():
    db = _db()
    product = _add(
        db,
        "BT-ONLY",
        description="Bluetooth LE module",
        technologies=["bluetooth"],
    )

    score = score_product(
        product,
        MatchRequest(
            technologies=["bluetooth"],
            bluetooth_required=True,
        ),
    )

    assert score is not None
    capability_reasons = [
        reason for reason in score["reasons"]
        if "bluetooth" in reason.lower() and "capability" in reason.lower()
    ]
    assert len(capability_reasons) == 1


def test_bluetooth_only_scope_beats_wifi_bluetooth_when_technical_fit_ties():
    db = _db()
    focused = _add(
        db,
        "BT-ONLY",
        description="Bluetooth LE module",
        technologies=["bluetooth"],
    )
    multiradio = _add(
        db,
        "WIFI-BT",
        category="Wi-Fi",
        description="Wi-Fi 6 + Bluetooth multiradio module",
        technologies=["wifi", "bluetooth"],
        wifi_generation="6",
    )

    request = MatchRequest(
        technologies=["bluetooth"],
        bluetooth_required=True,
    )
    focused_score = score_product(focused, request)
    multi_score = score_product(multiradio, request)

    assert focused_score["match_percent"] == multi_score["match_percent"]
    assert focused_score["solution_scope_score"] == 100
    assert multi_score["solution_scope_score"] < focused_score["solution_scope_score"]
    assert multi_score["extra_technologies"] == ["wifi"]


def test_scope_fit_is_used_before_evidence_for_equal_technical_score():
    focused = {
        "match_percent": 100,
        "solution_scope_score": 100,
        "evidence_score": 10,
        "evidence_summary": {"verified": 0, "conflicting": 0},
        "_evidence_completeness": 0,
        "product": {"features": {"imported_live": True}},
    }
    multiradio = {
        "match_percent": 100,
        "solution_scope_score": 85,
        "evidence_score": 100,
        "evidence_summary": {"verified": 5, "conflicting": 0},
        "_evidence_completeness": 10,
        "product": {"features": {"imported_live": True}},
    }

    assert evidence_sort_key(focused) > evidence_sort_key(multiradio)


def test_version_open_is_treated_as_answered_by_adaptive_engine():
    db = _db()
    for index in range(8):
        _add(
            db,
            f"B-{index}",
            description="Bluetooth LE 5.3 module",
            technologies=["bluetooth"],
            architecture="open" if index < 4 else "host",
            antenna="internal" if index % 2 else "external",
        )
    db.commit()

    result = choose_adaptive_question(
        db,
        MatchRequest(
            product_domain="connectivity",
            technologies=["bluetooth"],
            bluetooth_required=True,
            bluetooth_version_min=None,
        ),
    )

    assert result["question"] is not None
    assert result["question"]["key"] != "bluetoothRequirement"
    assert result["question"]["key"] in {"architecture", "antenna"}
