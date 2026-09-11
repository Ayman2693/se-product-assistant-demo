import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.catalog_sources import CATALOG_SOURCES
from app.db import Base
from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.adaptive_questions import choose_adaptive_question
from app.services.engineering_features import extract_engineering_features
from app.services.engineering_profiles import CATEGORY_PROFILES, profile_for_category
from app.services.feature_extractor import extract_features, feature_values_for_model
from app.services.matcher import score_product
from app.services.requirement_parser import interpret_text


def _product(part_number: str, category: str, description: str) -> Product:
    product = Product(
        part_number=part_number,
        manufacturer="Test",
        category=category,
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
        category=category,
        description=description,
        tags=[],
    )
    product.features = ProductFeature(
        product_id=1,
        imported_live=True,
        **feature_values_for_model(extracted),
    )
    return product


def test_every_configured_se_category_has_engineering_profile():
    configured = {source["category"] for source in CATALOG_SOURCES}
    assert configured == set(CATEGORY_PROFILES)
    assert len(configured) == 51
    assert all(profile_for_category(category) for category in configured)


def test_crystal_features_are_normalized():
    features = extract_engineering_features(
        "Crystals",
        "32.768 kHz quartz crystal SMD 9 pF ±20 ppm ESR 70 kOhm -40/+85°C",
    )
    assert features["frequency_hz"] == 32768.0
    assert features["load_capacitance_pf"] == 9.0
    assert features["frequency_tolerance_ppm"] == 20.0
    assert features["esr_ohm"] == 70000.0
    assert features["mounting"] == "smd"
    assert features["temperature_min_c"] == -40.0
    assert features["temperature_max_c"] == 85.0


def test_oscillator_features_are_normalized():
    features = extract_engineering_features(
        "Oscillators",
        "TCXO 50 MHz 3.3 V LVCMOS frequency stability ±0.5 ppm phase jitter 0.3 ps SMD -40/+85°C",
    )
    assert features["frequency_hz"] == 50_000_000.0
    assert features["oscillator_type"] == "tcxo"
    assert features["output_type"] == "lvcmos"
    assert features["frequency_stability_ppm"] == 0.5
    assert features["phase_jitter_ps"] == 0.3
    assert features["mounting"] == "smd"


def test_choke_features_are_normalized():
    features = extract_engineering_features(
        "Chokes",
        "Common-mode choke 100 uH 2 A DCR 0.15 Ohm impedance 600 Ohm @ 100 MHz SMD -40/+125°C",
    )
    assert features["choke_type"] == "common_mode"
    assert features["inductance_uh"] == 100.0
    assert features["rated_current_a"] == 2.0
    assert features["dc_resistance_ohm"] == 0.15
    assert features["impedance_ohm"] == 600.0
    assert features["test_frequency_hz"] == 100_000_000.0


def test_sensor_relay_display_storage_profiles_extract_real_discriminators():
    pressure = extract_engineering_features(
        "Pressure Sensors",
        "Pressure sensor 0-10 bar accuracy ±0.5% I2C 3.3 V SMD",
    )
    assert pressure["pressure_range_kpa"] == 1000.0
    assert pressure["accuracy_pct"] == 0.5
    assert pressure["interface"] == ["i2c"]

    relay = extract_engineering_features(
        "Relays",
        "Power relay SPDT coil 12 V contact 10 A 250 V THT",
    )
    assert relay["relay_type"] == "power"
    assert relay["contact_form"] == "spdt"
    assert relay["coil_voltage_v"] == 12.0
    assert relay["contact_current_a"] == 10.0
    assert relay["contact_voltage_v"] == 250.0

    display = extract_engineering_features(
        "TFT Displays",
        '7 inch TFT 800x480 MIPI capacitive touch 3.3 V',
    )
    assert display["display_size_in"] == 7.0
    assert display["resolution"] == "800×480"
    assert display["interface"] == ["mipi"]
    assert display["touch"] is True

    storage = extract_engineering_features(
        "Flash Storage",
        "Industrial NVMe SSD 512 GB M.2 -40/+85°C",
    )
    assert storage["storage_capacity_gb"] == 512.0
    assert storage["storage_interface"] == "nvme"


def test_natural_language_crystal_request_populates_universal_requirements():
    parsed = interpret_text("I need a 32.768 kHz crystal, 9 pF load capacitance and ±20 ppm")
    req = parsed["requirements"]
    assert req["catalog_category"] == "Crystals"
    assert req["engineering_requirements"]["frequency_hz"] == 32768.0
    assert req["engineering_requirements"]["load_capacitance_pf"] == 9.0
    assert req["engineering_requirements"]["frequency_tolerance_ppm"] == 20.0


def test_crystal_matcher_filters_by_engineering_requirements():
    wanted = _product("XTAL-9PF", "Crystals", "32.768 kHz crystal SMD 9 pF ±20 ppm")
    wrong_load = _product("XTAL-125PF", "Crystals", "32.768 kHz crystal SMD 12.5 pF ±20 ppm")

    request = MatchRequest(
        product_domain="timing",
        catalog_category="Crystals",
        technologies=["timing"],
        engineering_requirements={
            "frequency_hz": 32768,
            "load_capacitance_pf": 9,
            "frequency_tolerance_ppm": 20,
        },
    )

    good = score_product(wanted, request)
    bad = score_product(wrong_load, request)
    assert good is not None
    assert good["match_percent"] == 100
    assert any("Load capacitance" in reason for reason in good["reasons"])
    assert bad is None


def test_choke_matcher_rejects_known_current_or_inductance_mismatch():
    good = _product("CHOKE-A", "Chokes", "Common-mode choke 100 uH 2 A SMD")
    weak = _product("CHOKE-B", "Chokes", "Common-mode choke 47 uH 0.5 A SMD")

    request = MatchRequest(
        product_domain="components",
        catalog_category="Chokes",
        engineering_requirements={
            "choke_type": "common_mode",
            "inductance_uh": 100,
            "rated_current_a": 1.5,
        },
    )
    assert score_product(good, request) is not None
    assert score_product(weak, request) is None


def test_adaptive_engine_asks_the_field_that_actually_splits_crystals():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    for part_number, load_cap in [("A", "9 pF"), ("B", "12.5 pF")]:
        description = f"32.768 kHz crystal SMD {load_cap} ±20 ppm"
        product = Product(
            part_number=part_number,
            manufacturer="Test",
            category="Crystals",
            description=description,
            tags_json="[]",
            product_url="https://example.invalid",
            lifecycle="",
            availability="",
            exact=True,
        )
        db.add(product)
        db.flush()
        extracted = extract_features(
            part_number=part_number,
            manufacturer="Test",
            category="Crystals",
            description=description,
            tags=[],
        )
        db.add(ProductFeature(
            product_id=product.id,
            imported_live=True,
            **feature_values_for_model(extracted),
        ))
    db.commit()

    response = choose_adaptive_question(
        db,
        MatchRequest(product_domain="timing", catalog_category="Crystals", technologies=["timing"]),
    )

    question = response["question"]
    assert question is not None
    assert question["key"] == "engineering:load_capacitance_pf"
    assert "load capacitance" in question["text"].lower()
    assert {option["label"] for option in question["options"]} >= {"9 pF", "12.5 pF"}
