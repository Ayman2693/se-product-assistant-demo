from pathlib import Path

APP = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "App.tsx"
).read_text(encoding="utf-8")


def test_initial_greeting_identifies_se_product_assistant():
    assert "I am the SE Product Assistant. How can I help you?" in APP


def test_top_level_connectivity_choice_uses_bluetooth_not_bluetooth_le():
    assert '{ label: "Bluetooth", value: ["bluetooth"] }' in APP


def test_match_card_is_cleaner():
    assert '"technical match"' in APP
    assert 'return tr(language, "Catalog-supported"' in APP
    assert 'return tr(language, "Verified"' in APP
    assert 'return tr(language, "Needs verification"' in APP
    assert "✓ {customerEvidenceBadge" not in APP
    assert "{evidenceStatusIcon(item.status)}" in APP


def test_result_followup_is_linked_to_action_not_generic_project_questions():
    assert "What would you like to do next?" in APP
    assert "Technical review with an SE FAE" in APP
    assert "Price / availability / samples" in APP
    assert "Which result should the SE FAE review?" in APP
    assert "What should the FAE focus on?" in APP


def test_handoff_context_explicitly_does_not_change_ranking():
    assert "These handoff details do <strong>not</strong> change the technical ranking." in APP
    assert "These details do <strong>not</strong> change the technical ranking." in APP


def test_old_partner_question_is_not_in_new_commercial_flow():
    commercial_start = APP.index("function commercialQuestionFor(")
    commercial_end = APP.index("function isCommercialKey", commercial_start)
    commercial = APP[commercial_start:commercial_end]
    assert "projectPartners" not in commercial
    assert "designSituation" not in commercial
