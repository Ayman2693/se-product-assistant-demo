from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.matcher import score_product
from app.services.requirement_parser import interpret_text


def make_wifi_product(generation: str):
    p = Product(
        part_number=f"WIFI-{generation}",
        manufacturer="Test",
        category="Wi-Fi Modules",
        description=f"Wi-Fi {generation} wireless module",
        tags_json='["Wi-Fi"]',
    )
    p.features = ProductFeature(
        technologies_json='["wifi"]',
        wifi_generation=generation,
        raw_features_json="{}",
    )
    return p


def test_parser_collects_wifi_5_and_wifi_6():
    req = interpret_text("I need Wi-Fi 5 or Wi-Fi 6")["requirements"]
    assert req["wifi_generation"] == ["5", "6"]


def test_parser_detects_wifi_5():
    req = interpret_text("I need an 802.11ac module")["requirements"]
    assert req["wifi_generation"] == ["5"]


def test_matcher_treats_selected_generations_as_or():
    req = MatchRequest(
        technologies=["wifi"],
        wifi_generation=["5", "6"],
    )
    assert score_product(make_wifi_product("5"), req) is not None
    assert score_product(make_wifi_product("6"), req) is not None
    assert score_product(make_wifi_product("4"), req) is None


def test_matcher_allows_single_selected_generation():
    req = MatchRequest(
        technologies=["wifi"],
        wifi_generation=["5"],
    )
    assert score_product(make_wifi_product("5"), req) is not None
    assert score_product(make_wifi_product("6"), req) is None
