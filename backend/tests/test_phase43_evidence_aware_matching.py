from types import SimpleNamespace

from app.services.evidence_matcher import (
    _criterion_result,
    _supports,
    _summary,
)


def row(
    *,
    field_name,
    normalized_value,
    status,
    value_text=None,
    document_id=None,
    confidence=0.8,
):
    return SimpleNamespace(
        id=1,
        field_name=field_name,
        normalized_value=normalized_value,
        value_text=value_text or str(normalized_value),
        verification_status=status,
        source_type="product_summary" if document_id else "catalog_description",
        source_title="Test source",
        source_url="https://example.com/test.pdf",
        document_id=document_id,
        confidence=confidence,
        locations=[],
    )


def test_bluetooth_minimum_version():
    assert _supports("bluetooth_version", "5.4", "5.3")
    assert not _supports("bluetooth_version", "5.2", "5.3")


def test_external_antenna_accepts_both():
    assert _supports("antenna", "both", "external")


def test_verified_beats_inferred():
    criterion = {
        "key": "wifi_generation",
        "label": "Wi-Fi generation",
        "field": "wifi_generation",
        "expected": "6",
    }
    result = _criterion_result(
        criterion,
        [
            row(
                field_name="wifi_generation",
                normalized_value="6",
                status="inferred",
                confidence=0.8,
            ),
            row(
                field_name="wifi_generation",
                normalized_value="6",
                status="verified",
                document_id=9,
                confidence=0.97,
            ),
        ],
    )
    assert result["status"] == "verified"


def test_unknown_multi_value_is_not_conflict():
    criterion = {
        "key": "technology:gnss",
        "label": "GNSS capability",
        "field": "technology",
        "expected": "gnss",
    }
    result = _criterion_result(
        criterion,
        [
            row(
                field_name="technology",
                normalized_value="wifi",
                status="verified",
                document_id=9,
            )
        ],
    )
    assert result["status"] == "not_verified"


def test_evidence_score_is_not_technical_score():
    summary = _summary([
        {"status": "verified"},
        {"status": "inferred"},
        {"status": "not_verified"},
    ])
    assert summary["total"] == 3
    assert summary["verified"] == 1
    assert summary["inferred"] == 1
    assert 0 < summary["evidence_score"] < 100
