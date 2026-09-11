from pathlib import Path

APP = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "App.tsx"
).read_text(encoding="utf-8")


def test_frontend_supports_dynamic_engineering_question_keys():
    assert '| `engineering:${string}`' in APP
    assert 'activeQuestion.startsWith("engineering:")' in APP
    assert 'key.startsWith("engineering:")' in APP


def test_frontend_sends_universal_engineering_requirements_to_backend():
    assert "engineering_requirements: Object.fromEntries" in APP
    assert "answered_engineering_fields: req.answeredEngineering ?? []" in APP


def test_frontend_flattens_engineering_requirements_in_profile_panel():
    assert '...Object.entries(requirements.engineering ?? {}).map(' in APP
    assert '`engineering:${key}`' in APP
