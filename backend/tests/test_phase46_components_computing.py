from app.services.requirement_parser import interpret_text


def test_capacitor_plural_routes_directly():
    r = interpret_text("I need capacitors for my design")["requirements"]
    assert r["product_domain"] == "components"
    assert r["catalog_category"] == "Capacitors"


def test_german_capacitor_routes_directly():
    r = interpret_text("Ich suche einen Kondensator")["requirements"]
    assert r["product_domain"] == "components"
    assert r["catalog_category"] == "Capacitors"


def test_smarc_routes_to_com():
    r = interpret_text("I need a SMARC module")["requirements"]
    assert r["product_domain"] == "computing"
    assert r["catalog_category"] == "Computer on Modules"


def test_picoitx_routes_to_sbc():
    r = interpret_text("I need a PicoITX board")["requirements"]
    assert r["product_domain"] == "computing"
    assert r["catalog_category"] == "Single Board Computer"


def test_generic_components_domain():
    r = interpret_text("I am looking for electronic components")["requirements"]
    assert r["product_domain"] == "components"


def test_generic_computing_domain():
    r = interpret_text("I am looking for an embedded computing solution")["requirements"]
    assert r["product_domain"] == "computing"
