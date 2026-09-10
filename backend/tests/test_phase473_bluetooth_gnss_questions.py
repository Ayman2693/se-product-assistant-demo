from app.services.requirement_parser import QUESTION_MAP, interpret_text


def test_gnss_question_is_more_customer_friendly():
    q = QUESTION_MAP["gnss_precision"]
    assert q["text"] == "What positioning performance does your application need?"
    assert "Standard GNSS / meter-level" in q["options"]
    assert "High precision / centimeter-level (RTK)" in q["options"]
    assert "No fixed accuracy / not sure" in q["options"]


def test_bluetooth_minimum_versions_parse():
    for version in ("5.0", "5.1", "5.2", "5.3", "5.4", "6.0"):
        req = interpret_text(f"I need Bluetooth LE {version} or newer")["requirements"]
        assert req["bluetooth_required"] is True
        assert req["bluetooth_version_min"] == version


def test_rtk_maps_to_centimeter_level():
    req = interpret_text("I need RTK centimeter-level GNSS")["requirements"]
    assert req["gnss_precision"] == "cm"


def test_l1_l5_dual_band_is_detected():
    req = interpret_text("I need dual-band GNSS L1 + L5")["requirements"]
    assert req["gnss_dual_band"] is True
