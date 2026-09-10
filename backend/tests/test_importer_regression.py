from app.catalog_sources import CATALOG_SOURCES

def test_lte_filter_does_not_match_filter_accessories():
    needle = "lte"
    selected = [x for x in CATALOG_SOURCES if needle in x["category"].lower()]
    names = [x["category"] for x in selected]
    assert "LTE" in names
    assert "LTE-M / NB-IoT" in names
    assert "EMI Accessories" not in names
