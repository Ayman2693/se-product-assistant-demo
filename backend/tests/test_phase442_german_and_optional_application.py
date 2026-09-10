from app.services.requirement_parser import interpret_text, missing_requirements


def test_german_pressure_sensor_request():
    result = interpret_text(
        "Ich suche einen Drucksensor mit I2C für eine industrielle Pumpe"
    )["requirements"]
    assert result["product_domain"] == "sensors"
    assert result["catalog_category"] == "Pressure Sensors"
    assert result["generic_interface"] == "i2c"
    assert "sensor" in result["technologies"]


def test_german_wifi_request():
    result = interpret_text(
        "Ich brauche ein host-basiertes Wi-Fi-6-Modul mit externer Antenne für Deutschland"
    )["requirements"]
    assert result["product_domain"] == "connectivity"
    assert "wifi" in result["technologies"]
    assert result["wifi_generation"] == "6"
    assert result["architecture"] == "host"
    assert result["antenna"] == "external"
    assert result["region"] == "EMEA/APAC"


def test_german_gnss_request():
    result = interpret_text(
        "Ich brauche RTK GNSS mit Zentimetergenauigkeit für die Landwirtschaft"
    )["requirements"]
    assert result["product_domain"] == "positioning"
    assert "gnss" in result["technologies"]
    assert result["gnss_precision"] == "cm"
    assert result["application"] == "agriculture / precision farming"


def test_application_is_context_not_mandatory():
    req = {
        "product_domain": "sensors",
        "catalog_category": "Pressure Sensors",
        "application": None,
    }
    assert "application" not in missing_requirements(req)


def test_antenna_is_requirement_not_domain_for_wifi_module():
    result = interpret_text(
        "Ich brauche ein Wi-Fi-6-Modul mit externer Antenne für Deutschland"
    )["requirements"]
    assert result["product_domain"] == "connectivity"
    assert result["catalog_category"] is None
    assert result["antenna"] == "external"


def test_antenna_only_request_stays_antenna_domain():
    result = interpret_text(
        "Ich suche eine externe Antenne für Wi-Fi"
    )["requirements"]
    assert result["product_domain"] == "antenna"
    assert result["catalog_category"] == "External Antennas"


def test_german_inflected_wifi_module_sentence():
    result = interpret_text(
        "Ich brauche ein host-basiertes Wi-Fi-6-Modul mit externer Antenne für Deutschland"
    )["requirements"]
    assert result["product_domain"] == "connectivity"
    assert result["technologies"] == ["wifi"]
    assert result["wifi_generation"] == "6"
    assert result["architecture"] == "host"
    assert result["antenna"] == "external"
    assert result["region"] == "EMEA/APAC"
