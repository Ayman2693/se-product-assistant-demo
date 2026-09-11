from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.adaptive_questions import choose_adaptive_question
from app.services.evidence_matcher import evidence_sort_key, recommendation_safety


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _add_host(db, pn, description):
    product = Product(
        part_number=pn,
        manufacturer="Test",
        category="Wi-Fi",
        description=description,
        tags_json="[]",
    )
    db.add(product)
    db.flush()
    db.add(ProductFeature(
        product_id=product.id,
        technologies_json='["wifi","bluetooth"]',
        has_bluetooth=True,
        wifi_generation="6",
        architecture="host",
        antenna="external",
        imported_live=True,
        raw_features_json="{}",
    ))
    db.flush()
    return product


def test_host_based_architecture_requires_host_interface_as_core_question():
    db = _db()
    _add_host(db, "HOST-SDIO", "Host-based Wi-Fi Bluetooth module SDIO")
    _add_host(db, "HOST-PCIE", "Host-based Wi-Fi Bluetooth module PCIe")
    db.commit()

    result = choose_adaptive_question(
        db,
        MatchRequest(
            product_domain="connectivity",
            technologies=["bluetooth"],
            bluetooth_required=True,
            architecture="host",
            antenna="external",
        ),
    )

    assert result["question"]["key"] == "hostInterface"
    assert result["question"]["mode"] == "qualification"
    assert result["question"]["required"] is True


def test_host_interface_no_preference_counts_as_answered():
    db = _db()
    _add_host(db, "HOST-SDIO", "Host-based Wi-Fi Bluetooth module SDIO")
    _add_host(db, "HOST-PCIE", "Host-based Wi-Fi Bluetooth module PCIe")
    db.commit()

    result = choose_adaptive_question(
        db,
        MatchRequest(
            product_domain="connectivity",
            technologies=["bluetooth"],
            bluetooth_required=True,
            architecture="host",
            antenna="external",
            answered_open_fields=["hostInterface"],
        ),
    )

    assert result["question"] is None or result["question"]["key"] != "hostInterface"


def test_unknown_explicit_requirement_requires_fae_verification():
    safety = recommendation_safety({
        "reasons": [
            "BLUETOOTH capability",
            "Not verified: Footprint <= 100 mm²",
        ],
        "criterion_evidence": [
            {"key": "technology:bluetooth", "label": "BLUETOOTH capability", "status": "inferred"},
            {"key": "max_footprint_mm2", "label": "Maximum footprint", "status": "not_verified"},
        ],
    })

    assert safety["recommendation_confidence"] == "fae_verification_required"
    assert safety["verification_required"] is True
    assert "Footprint <= 100 mm²" in safety["verification_issues"]


def test_inferred_only_fit_is_provisional():
    safety = recommendation_safety({
        "reasons": ["BLUETOOTH capability"],
        "criterion_evidence": [
            {"key": "technology:bluetooth", "label": "BLUETOOTH capability", "status": "inferred"}
        ],
    })
    assert safety["recommendation_confidence"] == "provisional_fit"
    assert safety["verification_required"] is False


def test_all_requested_evidence_verified_is_verified_fit():
    safety = recommendation_safety({
        "reasons": ["BLUETOOTH capability", "Architecture: host"],
        "criterion_evidence": [
            {"key": "technology:bluetooth", "label": "BLUETOOTH capability", "status": "verified"},
            {"key": "architecture", "label": "Architecture", "status": "verified"},
        ],
    })
    assert safety["recommendation_confidence"] == "verified_fit"
    assert safety["verification_required"] is False


def test_conflict_requires_fae_verification():
    safety = recommendation_safety({
        "reasons": ["Architecture: host"],
        "criterion_evidence": [
            {"key": "architecture", "label": "Architecture", "status": "conflicting"}
        ],
    })
    assert safety["recommendation_confidence"] == "fae_verification_required"
    assert "Architecture" in safety["verification_issues"]


def test_safety_rank_breaks_equal_technical_scope_ties():
    verified = {
        "match_percent": 100,
        "solution_scope_score": 100,
        "_recommendation_safety_rank": 2,
        "evidence_score": 50,
        "evidence_summary": {"verified": 1, "conflicting": 0},
        "_evidence_completeness": 1,
        "product": {"features": {"imported_live": True}},
    }
    review = {
        "match_percent": 100,
        "solution_scope_score": 100,
        "_recommendation_safety_rank": 0,
        "evidence_score": 100,
        "evidence_summary": {"verified": 4, "conflicting": 0},
        "_evidence_completeness": 4,
        "product": {"features": {"imported_live": True}},
    }
    assert evidence_sort_key(verified) > evidence_sort_key(review)
