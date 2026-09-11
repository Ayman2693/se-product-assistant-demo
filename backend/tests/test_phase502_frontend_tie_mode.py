from pathlib import Path

APP = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "App.tsx"
).read_text(encoding="utf-8")


def test_frontend_sends_explicit_open_optional_fields():
    assert "answered_open_fields" in APP
    assert 'req.antennaConnector === "No preference"' in APP
    assert 'req.maxFootprint === "No fixed limit"' in APP


def test_frontend_explains_deep_tie_question():
    assert "top-ranked candidates that are still technically tied" in APP
    assert 'adaptive.mode === "tie_break"' in APP
