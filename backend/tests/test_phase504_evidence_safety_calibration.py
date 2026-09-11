from app.services.evidence_matcher import (
    _catalog_match_fallback,
    recommendation_safety,
)


def test_positive_wifi_reason_promotes_missing_evidence_to_inferred():
    criterion = {
        "key": "technology:wifi",
        "label": "WIFI capability",
        "field": "technology",
        "expected": "wifi",
    }
    item = {
        "key": "technology:wifi",
        "label": "WIFI capability",
        "requested_value": "wifi",
        "status": "not_verified",
    }
    result = {
        "product": {"product_url": "https://example.com/iris"},
        "reasons": ["WIFI capability"],
    }

    promoted = _catalog_match_fallback(criterion, item, result)

    assert promoted["status"] == "inferred"
    assert promoted["source_type"] == "structured_catalog_fallback"
    assert promoted["evidence_value"] == "WIFI capability"


def test_positive_architecture_and_wifi_generation_are_inferred():
    cases = [
        (
            {
                "key": "architecture",
                "label": "Architecture",
                "field": "architecture",
                "expected": "open",
            },
            ["Architecture: open"],
        ),
        (
            {
                "key": "wifi_generation",
                "label": "Wi-Fi generation",
                "field": "wifi_generation",
                "expected": ["5", "6", "6E"],
            },
            ["Acceptable generation: Wi-Fi 5 / Wi-Fi 6 / Wi-Fi 6E"],
        ),
    ]

    for criterion, reasons in cases:
        item = {
            "key": criterion["key"],
            "label": criterion["label"],
            "requested_value": str(criterion["expected"]),
            "status": "not_verified",
        }
        promoted = _catalog_match_fallback(
            criterion,
            item,
            {"product": {"product_url": ""}, "reasons": reasons},
        )
        assert promoted["status"] == "inferred"


def test_missing_evidence_alone_is_provisional_not_fae():
    safety = recommendation_safety({
        "reasons": ["WIFI capability", "Architecture: open"],
        "criterion_evidence": [
            {"label": "WIFI capability", "status": "not_verified"},
            {"label": "Architecture", "status": "not_verified"},
        ],
    })

    assert safety["recommendation_confidence"] == "provisional_fit"
    assert safety["verification_required"] is False


def test_matcher_warning_remains_hard_fae_escalation():
    safety = recommendation_safety({
        "reasons": [
            "WIFI capability",
            "Not verified: Footprint <= 100 mm²",
        ],
        "criterion_evidence": [
            {"label": "WIFI capability", "status": "inferred"},
            {"label": "Maximum footprint", "status": "not_verified"},
        ],
    })

    assert safety["recommendation_confidence"] == "fae_verification_required"
    assert safety["verification_required"] is True
    assert "Footprint <= 100 mm²" in safety["verification_issues"]


def test_conflicting_evidence_remains_hard_fae_escalation():
    safety = recommendation_safety({
        "reasons": ["Architecture: open"],
        "criterion_evidence": [
            {"label": "Architecture", "status": "conflicting"},
        ],
    })

    assert safety["recommendation_confidence"] == "fae_verification_required"
    assert safety["verification_required"] is True
