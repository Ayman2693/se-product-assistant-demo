from collections import Counter

from app.catalog_sources import CATALOG_SOURCES, source_seed_paths
from app.services.adaptive_questions import _dynamic_options
from app.services.catalog_importer import _detail_feature_values
from app.services.engineering_features import extract_engineering_features
from app.services.engineering_profiles import field_spec, profile_for_category
from app.services.requirement_parser import interpret_text


def test_other_rf_parent_crawls_all_current_se_child_sections():
    source = next(row for row in CATALOG_SOURCES if row["category"] == "Other RF Components")
    assert source_seed_paths(source) == [
        "/en/rfother/", "/en/maritimecom/", "/en/wirelinetelecom/",
        "/en/wirelessdata/", "/en/2-way-radio/", "/en/rfbuildblocks/",
    ]


def test_requested_short_range_profiles_have_professional_filters():
    assert [s.key for s in profile_for_category("Wi-Fi")][:5] == [
        "wifi_band", "wifi_operation_mode", "wireless_chip", "wifi_standard", "antenna_option"
    ]
    assert [s.key for s in profile_for_category("Multiradio")][:6] == [
        "wireless_type", "wireless_chip", "wifi_standard", "bluetooth_standard", "antenna_option", "wireless_software"
    ]
    assert [s.key for s in profile_for_category("Bluetooth LE")][:3] == [
        "bluetooth_standard", "antenna_option", "bluetooth_max_range_m"
    ]
    assert [s.key for s in profile_for_category("Bluetooth Classic + LE")][:3] == [
        "bluetooth_standard", "antenna_option", "bluetooth_max_range_m"
    ]
    assert [s.key for s in profile_for_category("Short Range Evaluation")][0] == "wireless_chip"
    assert [s.key for s in profile_for_category("Other RF Components")][:2] == ["rf_application", "rf_component_type"]


def test_wifi_filters_extract_from_se_style_text():
    f = extract_engineering_features(
        "Wi-Fi",
        "Type: host based Chip: NXP IW416 Wi-Fi Standard: Wi-Fi 4 dual-band "
        "Antenna Option: 2 antenna pins Operation modes: Access point Station Wi-Fi Direct 2.4 and 5 GHz",
    )
    assert f["wireless_chip"] == "nxp_iw416"
    assert f["wifi_standard"] == "wifi4_dual"
    assert f["wifi_band"] == "dual_24_5"
    assert set(f["wifi_operation_mode"]) == {"access_point", "station", "wifi_direct"}
    assert f["antenna_option"] == "two_antenna_pins"


def test_bluetooth_filters_extract_standard_antenna_and_range():
    f = extract_engineering_features(
        "Bluetooth Classic + LE",
        "Bluetooth Standard: v4.2 LE and BR/EDR Antenna Option: Internal antenna max. Range: 400 m",
    )
    assert f["bluetooth_standard"] == "v4.2_dual"
    assert f["antenna_option"] == "internal_antenna"
    assert f["bluetooth_max_range_m"] == 400.0


def test_multiradio_filters_extract():
    f = extract_engineering_features(
        "Multiradio",
        "Type: host based Chip: NXP IW611 Wi-Fi Standard: Wi-Fi 6 dual-band "
        "Bluetooth Standard: v5.3 LE Antenna Option: 2 U.FL connectors Software: Linux / Android",
    )
    assert f["wireless_type"] == "host_based"
    assert f["wireless_chip"] == "nxp_iw611"
    assert f["wifi_standard"] == "wifi6_dual"
    assert f["bluetooth_standard"] == "v5.3_le"
    assert f["antenna_option"] == "two_ufl_connectors"
    assert f["wireless_software"] == "linux_android"


def test_other_rf_uses_se_branch_and_component_type():
    f = extract_engineering_features(
        "Other RF Components",
        "Maritime Communication CMX7032L9 AIS Class B Baseband Processor with RF Synthesiser",
    )
    assert f["rf_application"] == "maritime"
    assert f["rf_component_type"] == "baseband_processor"


def test_detail_parser_collects_wireless_filter_values():
    html = """<html><body><div>
    Form factor: MAYA Type: host based Chip: NXP IW416 Wi-Fi Standard: Wi-Fi 4 dual-band
    Bluetooth Standard: v5.2 LE Antenna Option: 2 antenna pins Software: Linux / Android
    max. Range: 400 m Operation modes: Access point Station Wi-Fi Direct Downloads
    </div></body></html>"""
    v = _detail_feature_values(html)
    assert v["Chip"] == "NXP IW416"
    assert "Wi-Fi 4 dual-band" in v["Wi-Fi Standard"]
    assert "v5.2 LE" in v["Bluetooth Standard"]
    assert "2 antenna pins" in v["Antenna Option"]
    assert "Access point" in v["Operation modes"]


def test_fixed_choices_always_end_with_open_option():
    spec = field_spec("bluetooth_standard")
    options = _dynamic_options("engineering:bluetooth_standard", Counter(), spec)
    assert options[-1] == {"label": "Not determined / open", "value": "__open__"}


def test_parser_understands_multiradio_and_classic_plus_le():
    multi = interpret_text("I need a Wi-Fi and Bluetooth module")["requirements"]
    assert multi["catalog_category"] == "Multiradio"
    assert set(multi["technologies"]) == {"wifi", "bluetooth"}

    dual = interpret_text("I need Bluetooth Classic and LE in one module")["requirements"]
    assert dual["catalog_category"] == "Bluetooth Classic + LE"
    assert dual["technologies"] == ["bluetooth"]


def test_parser_understands_evaluation_and_other_rf():
    assert interpret_text("I need a Bluetooth evaluation kit")["requirements"]["catalog_category"] == "Short Range Evaluation"
    assert interpret_text("I need an RF power amplifier")["requirements"]["catalog_category"] == "Other RF Components"
