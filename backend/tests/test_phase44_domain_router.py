from app.schemas import MatchRequest
from app.services.matcher import _catalog_category_matches, _generic_interfaces
from app.services.requirement_parser import interpret_text


def test_generic_sensor_routes_to_sensor_domain():
    result = interpret_text("I need a sensor for my machine")["requirements"]
    assert result["product_domain"] == "sensors"
    assert "sensor" in result["technologies"]


def test_pressure_sensor_detects_category():
    result = interpret_text(
        "I need a pressure sensor with I2C for an industrial pump"
    )["requirements"]
    assert result["product_domain"] == "sensors"
    assert result["catalog_category"] == "Pressure Sensors"
    assert result["generic_interface"] == "i2c"
    assert "sensor" in result["technologies"]


def test_wifi_module_stays_connectivity():
    result = interpret_text(
        "I need a Wi-Fi 6 host-based module for an industrial gateway"
    )["requirements"]
    assert result["product_domain"] == "connectivity"
    assert "wifi" in result["technologies"]


def test_gnss_only_routes_positioning():
    result = interpret_text("I need RTK GNSS for agriculture")["requirements"]
    assert result["product_domain"] == "positioning"
    assert "gnss" in result["technologies"]


def test_sensor_category_matching():
    assert _catalog_category_matches("Pressure Sensors", "Pressure Sensors")
    assert not _catalog_category_matches("Wi-Fi", "Pressure Sensors")


def test_generic_interfaces():
    found = _generic_interfaces("Digital pressure sensor with I2C and SPI interface")
    assert "i2c" in found
    assert "spi" in found


def test_new_match_fields_validate():
    request = MatchRequest(
        application="industrial IoT",
        product_domain="sensors",
        catalog_category="Pressure Sensors",
        generic_interface="i2c",
        technologies=["sensor"],
    )
    assert request.catalog_category == "Pressure Sensors"
