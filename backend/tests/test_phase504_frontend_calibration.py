from pathlib import Path

APP = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "App.tsx"
).read_text(encoding="utf-8")


def test_provisional_copy_is_not_hard_fae_language():
    assert "current SE catalog / structured product data supports the fit" in APP


def test_red_verification_issue_is_only_for_hard_escalation():
    assert "match.verification_required && match.verification_issues.length > 0" in APP
