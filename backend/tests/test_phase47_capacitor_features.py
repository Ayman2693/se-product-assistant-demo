import json

from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.feature_extractor import extract_features, feature_values_for_model
from app.services.matcher import score_product
from app.services.requirement_parser import interpret_text, missing_requirements


def make_cap(description: str):
    p = Product(
        part_number="TEST-CAP",
        manufacturer="Kemet",
        category="Capacitors",
        description=description,
        tags_json='["Kemet", "Capacitors", "Tantalum capacitors"]',
    )
    extracted = extract_features(
        p.part_number,
        p.manufacturer,
        p.category,
        p.description,
        ["Kemet", "Capacitors", "Tantalum capacitors"],
    )
    f = ProductFeature()
    for key, value in feature_values_for_model(extracted).items():
        setattr(f, key, value)
    p.features = f
    return p, extracted


def test_catalog_capacitor_feature_extraction():
    _, e = make_cap("Tantalum SMD capacitor 47 µF 25 V ±10% ESR 80 mOhm")
    raw = e["raw_features"]
    assert raw["capacitance_uf"] == 47
    assert raw["capacitor_voltage_v"] == 25
    assert raw["capacitor_tolerance_pct"] == 10
    assert raw["capacitor_technology"] == "Tantalum"
    assert raw["capacitor_mounting"] == "SMD"
    assert abs(raw["capacitor_esr_ohm"] - 0.08) < 1e-9
    assert raw["capacitor_theoretical_energy_j"] > 0


def test_customer_request_parser_extracts_engineering_values():
    r = interpret_text(
        "I need a 47 uF 25 V tantalum SMD capacitor ±10%, max ESR 100 mOhm"
    )["requirements"]
    assert r["catalog_category"] == "Capacitors"
    assert r["capacitance_uf"] == 47
    assert r["capacitor_voltage_v"] == 25
    assert r["capacitor_tolerance_pct"] == 10
    assert r["capacitor_technology"] == "Tantalum"
    assert r["capacitor_mounting"] == "SMD"
    assert abs(r["capacitor_esr_max_ohm"] - 0.1) < 1e-9


def test_capacitor_missing_questions_are_domain_specific():
    r = interpret_text("I need a capacitor")["requirements"]
    missing = missing_requirements(r)
    assert missing[:5] == [
        "capacitance_uf",
        "capacitor_voltage_v",
        "capacitor_technology",
        "capacitor_mounting",
        "capacitor_tolerance",
    ]


def test_matcher_accepts_higher_voltage_and_tighter_tolerance():
    p, _ = make_cap("Tantalum SMD capacitor 47 µF 25 V ±5% ESR 80 mOhm")
    req = MatchRequest(
        catalog_category="Capacitors",
        capacitance_uf=47,
        capacitor_voltage_v=16,
        capacitor_tolerance_pct=10,
        capacitor_technology="Tantalum",
        capacitor_mounting="SMD",
        capacitor_esr_max_ohm=0.1,
    )
    result = score_product(p, req)
    assert result is not None
    assert result["match_percent"] > 80


def test_matcher_rejects_known_low_voltage():
    p, _ = make_cap("Tantalum SMD capacitor 47 µF 10 V ±10%")
    req = MatchRequest(
        catalog_category="Capacitors",
        capacitance_uf=47,
        capacitor_voltage_v=16,
    )
    assert score_product(p, req) is None


def test_matcher_rejects_wrong_capacitance():
    p, _ = make_cap("Tantalum SMD capacitor 10 µF 25 V ±10%")
    req = MatchRequest(
        catalog_category="Capacitors",
        capacitance_uf=47,
        capacitor_voltage_v=16,
    )
    assert score_product(p, req) is None
def test_x7r_is_understood_as_ceramic_technology():
    r = interpret_text("100 nF 50 V X7R SMD capacitor ±10%")["requirements"]
    assert r["capacitor_technology"] == "Ceramic"
