from app.services.feature_extractor import extract_features

def test_wifi6_host_maya():
    x = extract_features(
        "MAYA-W266-00B",
        "u-blox",
        "Wi-Fi",
        "u-blox*Host-based Multiradio Module*Wi-Fi 6+BLE5.3 PCB ant. / ant. pin*10.4x14.3x1.9mm*NXP IW611",
        [],
    )
    assert x["wifi_generation"] == "6"
    assert x["architecture"] == "host"
    assert x["has_bluetooth"] is True
    assert "bluetooth" in x["technologies"]

def test_wifi5_jody_w263_not_wifi6():
    x = extract_features(
        "JODY-W263-00B",
        "u-blox",
        "Wi-Fi",
        "u-blox*Host-based Multiradio Module (Wi-F +BT/BLE) 802.11ac*SDIO*SISO*BT5*professional",
        [],
    )
    assert x["wifi_generation"] == "5"
    assert x["architecture"] == "host"
    assert "bluetooth" in x["technologies"]

def test_no_false_cellular_from_no_lte_filter():
    x = extract_features(
        "EMMY-W165-00B",
        "u-blox",
        "Wi-Fi",
        "u-blox*Multiradio Module (BT, Wi-Fi ac/abgn)* host-based*1 solder pads for ant.*13.8x19.8x2.5mm no LTE Filter",
        [],
    )
    assert "cellular" not in x["technologies"]
    assert x["wifi_generation"] == "5"

def test_part_number_not_temperature():
    x = extract_features(
        "M2-JODY-W377-10C",
        "SE Partner",
        "Wi-Fi",
        "M.2 card w. JODY-W377 module*WiFi 6 + BT 5.3 M.2 Type 2230 Key E embedded antennas included in the box",
        [],
    )
    assert x["temperature_min"] is None
    assert x["temperature_max"] is None
    assert x["wifi_generation"] == "6"
