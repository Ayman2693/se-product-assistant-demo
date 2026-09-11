from app.services.requirement_parser import interpret_text, missing_requirements

def test_wifi6_host_gateway_sentence():
    parsed = interpret_text(
        "I need a Wi-Fi 6 host-based module for an industrial gateway with external antennas."
    )["requirements"]

    assert parsed["application"] == "industrial gateway"
    assert parsed["technologies"] == ["wifi"]
    assert parsed["wifi_generation"] == ["6"]
    assert parsed["architecture"] == "host"
    assert parsed["antenna"] == "external"

def test_asset_tracker_sentence():
    parsed = interpret_text(
        "Battery powered global asset tracker with LTE Cat 1bis and GNSS."
    )["requirements"]

    assert parsed["application"] == "asset tracking"
    assert "cellular" in parsed["technologies"]
    assert "gnss" in parsed["technologies"]
    assert parsed["cellular_class"] == "Cat 1bis"
    assert parsed["region"] == "Global"
    assert parsed["low_power"] is True

def test_missing_gnss_precision():
    req = interpret_text(
        "Global asset tracker with Cat 1bis and GNSS."
    )["requirements"]
    missing = missing_requirements(req)
    assert "gnss_precision" in missing
