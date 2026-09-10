from app.services.feature_extractor import extract_features

def test_int_dot_antenna_is_internal():
    x = extract_features(
        "ANNA-B402-00B",
        "u-blox",
        "Bluetooth LE",
        "BT 5.1 LE module*int.antenna*openCPU nRF52833",
        [],
    )
    assert x["antenna"] == "internal"

def test_negative_low_power_evidence_is_recorded():
    x = extract_features(
        "NINA-B306-01B",
        "u-blox",
        "Bluetooth LE",
        "Bluetooth LE Open CPU module w/o low-power XTAL",
        [],
    )
    assert x["raw_features"]["low_power_negative"] is True
    assert x["raw_features"]["low_power_positive"] is False
