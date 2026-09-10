from app.services.feature_extractor import extract_features

def test_cat1bis_global_gnss():
    x = extract_features(
        "C16QS-WW-GNAN",
        "Cavli",
        "LTE",
        "CAVLI*C16QS*LTE Cat.1bis module*GNSS (L1) LGA*26.5x22.5x2.3mm*-30 to +85°C*worldwide",
        [],
    )
    assert "cellular" in x["technologies"]
    assert "gnss" in x["technologies"]
    assert x["cellular_class"] == "Cat 1bis"
    assert x["region"] == "Global"
    assert x["has_gnss"] is True
    assert x["form_factor"] == "LGA"
    assert x["temperature_min"] == -30
    assert x["temperature_max"] == 85
