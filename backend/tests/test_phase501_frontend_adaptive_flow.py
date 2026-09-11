from pathlib import Path


APP = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "App.tsx"
).read_text(encoding="utf-8")


def test_legacy_tiebreaker_bypass_is_removed():
    assert "function isTieBreakerKey" not in APP
    assert "if (isTieBreakerKey(key))" not in APP


def test_technical_answers_return_to_adaptive_engine():
    marker = "Every technical answer goes back through the adaptive engine."
    assert marker in APP
    assert "window.setTimeout(() => void askNext(next), 60);" in APP
