from app.services.feature_extractor import extract_features

def test_ww_part_number_maps_to_global():
    x = extract_features(
        "C16QS-WW-GNAN",
        "Cavli",
        "LTE",
        "CAVLI*C16QS*LTE Cat.1bis module*GNSS (L1) LGA*26.5x22.5x2.3mm*-30 to +85°C",
        [],
    )
    assert x["region"] == "Global"

def test_antenna_pin_maps_external():
    x = extract_features(
        "ALMA-B101-00B",
        "u-blox",
        "Bluetooth LE",
        "u-blox*Bluetooth 5.4 LE stand-alone module antenna-pin*nRF54H20*10.4x11.2x1.9mm*Open CPU",
        [],
    )
    assert x["antenna"] == "external"

def test_without_low_power_is_negative():
    x = extract_features(
        "NINA-B306-01B",
        "u-blox",
        "Bluetooth LE",
        "u-blox*Bluetooth 5.0 LE mod.+BT mesh*int.PCB ant. nRF52840*10x15x2.2mm*Open CPU*w/o low-power XTAL",
        [],
    )
    assert x["raw_features"]["low_power_positive"] is False
    assert x["raw_features"]["low_power_negative"] is True

def test_generic_low_power_is_positive():
    x = extract_features(
        "DEMO-LOWPOWER",
        "Demo",
        "Bluetooth LE",
        "Bluetooth LE Open CPU module with integrated antenna and ultra-low-power operation",
        [],
    )
    assert x["raw_features"]["low_power_positive"] is True
    assert x["raw_features"]["low_power_negative"] is False
