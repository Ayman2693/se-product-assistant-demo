from pathlib import Path

APP = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "App.tsx"
).read_text(encoding="utf-8")


def test_frontend_asks_antenna_qualification_questions():
    assert "Which radio system must the antenna support?" in APP
    assert "Which GNSS band capability do you need?" in APP
    assert "Which Wi-Fi / Bluetooth frequency coverage do you need?" in APP
    assert "Do you need an active or passive GNSS antenna?" in APP


def test_frontend_sends_antenna_filters_to_matcher():
    assert "antenna_application: req.antennaApplication ?? null" in APP
    assert "antenna_band:" in APP
    assert "antenna_active:" in APP


def test_tied_top_products_are_not_presented_as_fake_number_one():
    assert "Top technical match · tied" in APP
