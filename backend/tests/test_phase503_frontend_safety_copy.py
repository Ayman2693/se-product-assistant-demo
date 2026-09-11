from pathlib import Path

APP = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "App.tsx"
).read_text(encoding="utf-8")


def test_unknown_unique_result_uses_provisional_safety_wording():
    assert "strongest <strong>provisional</strong> match" in APP
    assert "Datasheet / SE FAE verification is recommended before design-in." in APP


def test_three_confidence_states_are_exposed():
    assert '"verified_fit"' in APP
    assert '"provisional_fit"' in APP
    assert '"fae_verification_required"' in APP


def test_host_interface_has_core_wording():
    assert "Which host interface does your system support?" in APP
