import re

from app.services.evidence_service import _chunk_page, _normalize_pdf_text


def test_unicode_minus_is_normalized():
    text = _normalize_pdf_text("Operating temperature −40 °C to +85 °C")
    assert "-40 °C" in text


def test_chunk_page_keeps_negative_temperature():
    chunks = _chunk_page("Operating temperature −40 °C to +85 °C")
    assert chunks == ["Operating temperature -40 °C to +85 °C"]


def _extract_bt_version_like_service(text: str):
    for candidate in re.finditer(
        r"\bBluetooth(?:\s+Low\s+Energy|\s+LE)?\s*(?:version\s*|v\s*)?([4-6](?:\.\d+)?)\b",
        text,
        re.I,
    ):
        suffix = text[candidate.end():candidate.end() + 20]
        if re.match(r"\s*[- ]?wire\b", suffix, re.I):
            continue
        return candidate.group(1)
    return None


def test_bluetooth_4_wire_is_not_a_version():
    assert _extract_bt_version_like_service("Bluetooth 4-wire high-speed UART") is None


def test_real_bluetooth_version_is_detected():
    assert _extract_bt_version_like_service("Bluetooth 5.4 supporting LE Audio") == "5.4"
