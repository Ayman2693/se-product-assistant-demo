def _keep_technology(value: str) -> bool:
    return value.lower() != "antenna"


def test_antenna_is_not_a_technology():
    assert _keep_technology("antenna") is False


def test_non_radio_catalog_technologies_are_preserved():
    for value in ["sensor", "storage", "display", "timing", "wifi", "bluetooth", "gnss", "cellular"]:
        assert _keep_technology(value) is True
