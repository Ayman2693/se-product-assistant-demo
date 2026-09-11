import json
from pathlib import Path

from app.catalog_sources import CATALOG_SOURCES
from app.services.adaptive_questions import QUESTION_TEXT

ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
SEED = json.loads((ROOT / "backend" / "data" / "products_seed.json").read_text(encoding="utf-8"))


def test_audio_codecs_are_bootstrapped_under_canonical_category():
    codecs = [row for row in SEED if row.get("category") == "Audio Codecs"]
    assert len(codecs) >= 10
    assert any(row.get("id") == "CMX655DQ6" for row in codecs)
    assert not any(row.get("id") == "CMX655DQ6" and row.get("category") == "Audio Codec" for row in SEED)


def test_audio_codec_live_source_has_coverage_guard():
    source = next(row for row in CATALOG_SOURCES if row["category"] == "Audio Codecs")
    assert source["path"] == "/en/audocodec/"
    assert source["minimum_expected_products"] >= 1


def test_gnss_questions_use_professional_accuracy_and_band_language():
    assert QUESTION_TEXT["gnssPrecision"] == "What positioning accuracy class is required for your application?"
    assert QUESTION_TEXT["gnssDualBand"] == "Which GNSS receiver band capability is required?"
    assert "Standard positioning — meter-level accuracy" in APP
    assert "High-precision positioning — centimeter-level RTK" in APP
    assert "Single-band L1 is sufficient" in APP
    assert "Dual-band L1 + L5 is required" in APP


def test_email_drafts_are_generated_after_handoff():
    assert "function commercialEmailDraft" in APP
    assert "function technicalEmailDraft" in APP
    assert "Suggested email to SE" in APP
    assert "Open email draft" in APP
    assert "price indication, MOQ, current availability/lead time, and sample availability" in APP


def test_opening_has_hello_and_restart_is_only_in_composer_area():
    assert "Hello.<br>I am the SE Product Assistant. How can I help you?" in APP
    assert 'className="restartUnderSend"' in APP
    assert 'className="restart" onClick={reset}' not in APP
    chat_header_start = APP.index('<div className="chatHeader">')
    chat_body_start = APP.index('<div className="chatBody"', chat_header_start)
    assert 'onClick={reset}' not in APP[chat_header_start:chat_body_start]
