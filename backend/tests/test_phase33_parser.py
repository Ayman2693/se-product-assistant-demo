from app.services.requirement_parser import interpret_text

def test_extended_natural_requirement():
    r = interpret_text(
        "I need Wi-Fi 6 host-based with SDIO, U.FL and Bluetooth 5.3 for an industrial gateway."
    )["requirements"]
    assert r["host_interface"] == "sdio"
    assert r["antenna_connector"] == "ufl"
    assert r["bluetooth_required"] is True
    assert r["bluetooth_version_min"] == "5.3"

def test_cellular_tiebreaker_text():
    r = interpret_text(
        "Global Cat 1bis tracker with GNSS L1+L5 in LGA form factor."
    )["requirements"]
    assert r["form_factor"] == "LGA"
    assert r["gnss_dual_band"] is True
