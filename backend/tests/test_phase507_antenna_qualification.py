import json

from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.feature_extractor import extract_features, feature_values_for_model
from app.services.matcher import score_product
from app.services.adaptive_questions import (
    _antenna_application_signal,
    _antenna_band_signal,
)


def _product(part_number: str, description: str) -> Product:
    product = Product(
        part_number=part_number,
        manufacturer="Test",
        category="SMD Antennas",
        description=description,
        tags_json="[]",
        product_url="https://example.invalid",
        lifecycle="",
        availability="",
        exact=True,
    )
    extracted = extract_features(
        part_number=part_number,
        manufacturer="Test",
        category="SMD Antennas",
        description=description,
        tags=[],
    )
    values = feature_values_for_model(extracted)
    product.features = ProductFeature(product_id=1, imported_live=True, **values)
    return product


def test_extractor_distinguishes_realistic_smd_antenna_examples():
    l1 = _product("AN-SR4G013", "GNSS antenna 1559-1609MHz SMD 15.6x3.3x4.4mm")
    multiband = _product("AN-SR4G053", "SMD antenna for GNSS 1164-1249+1559-1609MHz 16x8x1.7mm")
    wifi = _product("SZP-C-1W11", "PCB antenna Wi-Fi 6 + 6E SMD 9.0x5.8x1.1mm")
    active = _product("SZA-C-0G03", "Low Power Active GNSS SMD Antenna 9.0x7.0x1.5mm")
    passive = _product("TGCGGP254E02", "passive GNSS Patch antenna 25.1 x 25.1 x 4mm")

    assert _antenna_application_signal(l1) == "gnss"
    assert _antenna_band_signal(l1) == "gnss_l1"

    assert _antenna_application_signal(multiband) == "gnss"
    assert _antenna_band_signal(multiband) == "gnss_multiband"

    assert _antenna_application_signal(wifi) == "wifi_bt"
    assert _antenna_band_signal(wifi) == "wifi_6e"

    assert json.loads(active.features.raw_features_json)["antenna_active"] is True
    assert json.loads(passive.features.raw_features_json)["antenna_active"] is False


def test_gnss_application_hard_filters_wifi_antenna():
    gnss = _product("GNSS", "GNSS antenna 1559-1609MHz SMD")
    wifi = _product("WIFI", "Wi-Fi 6 + 6E SMD antenna")

    request = MatchRequest(
        product_domain="antenna",
        catalog_category="SMD Antennas",
        technologies=["antenna"],
        antenna_application="gnss",
        antenna_band="gnss_l1",
    )

    gnss_score = score_product(gnss, request)
    wifi_score = score_product(wifi, request)

    assert gnss_score is not None
    assert gnss_score["match_percent"] == 100
    assert wifi_score is None


def test_multiband_requirement_excludes_known_l1_only_antenna():
    l1 = _product("L1", "GNSS antenna 1559-1609MHz SMD")
    multiband = _product("MULTI", "Dual Band GNSS L1 / L2 / L5 SMD antenna")

    request = MatchRequest(
        product_domain="antenna",
        catalog_category="SMD Antennas",
        technologies=["antenna"],
        antenna_application="gnss",
        antenna_band="gnss_multiband",
    )

    assert score_product(l1, request) is None
    assert score_product(multiband, request) is not None


def test_active_passive_is_real_engineering_filter():
    active = _product("ACTIVE", "Active GNSS antenna L1 SMD")
    passive = _product("PASSIVE", "Passive GNSS antenna L1 SMD")

    request = MatchRequest(
        product_domain="antenna",
        catalog_category="SMD Antennas",
        technologies=["antenna"],
        antenna_application="gnss",
        antenna_band="gnss_l1",
        antenna_active=True,
    )

    assert score_product(active, request) is not None
    assert score_product(passive, request) is None
