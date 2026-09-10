from app.services.feature_extractor import extract_features

def test_nina_bgn_is_wifi4_standalone():
    x = extract_features(
        "NINA-W152-03B",
        "u-blox",
        "Wi-Fi",
        "u-blox*802.11bgn Wi-Fi & BT Stand-alone module int. antenna*connectivity SW*10.0x14.0 mm",
        [],
    )
    assert x["wifi_generation"] == "4"
    assert x["architecture"] == "standalone"
