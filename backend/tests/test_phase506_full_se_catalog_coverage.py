import asyncio

from app.catalog_sources import CATALOG_SOURCES, source_seed_paths
from app.services.catalog_importer import crawl_source


def _source(category: str) -> dict:
    return next(row for row in CATALOG_SOURCES if row["category"] == category)


def test_current_products_tree_is_represented_by_configured_sources():
    # Current SE /products/ tree leaves represented by one or more canonical
    # assistant sources. This is intentionally an internal coverage contract.
    expected_categories = {
        # Wireless / RF
        "LTE-M / NB-IoT", "LTE", "5G RedCap", "Cellular Evaluation",
        "Standard GNSS", "High Precision GNSS", "GNSS Timing",
        "Dead Reckoning", "GNSS Evaluation",
        "Bluetooth LE", "Multiradio", "Wi-Fi", "Bluetooth Classic + LE",
        "Short Range Evaluation",
        "External Antennas", "SMD Antennas", "Embedded Antennas",
        "Other RF Components",
        # Computing / Memory / Displays / Audio / Passives
        "Computer on Modules", "Single Board Computer", "Embedded Peripherals",
        "Flash Storage",
        "TFT Displays", "OLED Displays", "Character Displays",
        "Graphic Displays", "Smart Displays", "Display Driver IC",
        "Vibration", "Audio Codecs", "Capacitors",
        # Emech / EMI
        "Relays", "Contactors", "Switches", "Connectors", "Chokes",
        "EMI / EMC Filters", "EMI Accessories",
        # Sensors
        "Motion Sensors", "Pressure Sensors", "Force Sensors",
        "Airflow Sensors", "Humidity Sensors", "Temperature Sensors",
        "Hall / Magnetic Sensors", "Gas Sensors",
        # Timing
        "RTCs", "Oscillators", "Timing IC", "Crystals", "Timing Evaluation",
    }

    actual = {row["category"] for row in CATALOG_SOURCES}
    assert expected_categories <= actual


def test_critical_nested_timing_and_choke_listings_are_explicitly_seeded():
    assert source_seed_paths(_source("Crystals")) == [
        "/en/timxtal/",
        "/en/timxtalmhz/",
        "/en/timkhz/",
    ]
    assert source_seed_paths(_source("Oscillators")) == [
        "/en/timosc/",
        "/en/timoscmhz/",
        "/en/timosckhz/",
    ]
    assert source_seed_paths(_source("Timing IC")) == [
        "/en/timic/",
        "/en/timicnetsync/",
        "/en/timicjittercleaner/",
        "/en/timicbuffer/",
    ]
    assert source_seed_paths(_source("Chokes")) == [
        "/en/emechchokes/",
        "/en/emechchokecurrent/",
        "/en/emechchokessuppres/",
        "/en/emechchokesatur/",
    ]


def test_cross_prefix_khz_crystal_seed_is_preserved():
    # This is the concrete regression: /en/timkhz/ does not begin with
    # /en/timxtal and was therefore invisible to prefix-only child discovery.
    crystal = _source("Crystals")
    assert "/en/timkhz/" in crystal["extra_paths"]
    assert not "/en/timkhz/".rstrip("/").startswith("/en/timxtal".rstrip("/"))


class _FakeResponse:
    def __init__(self, url: str, text: str):
        self.url = url
        self.text = text

    def raise_for_status(self):
        return None


class _FakeClient:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.calls: list[str] = []

    async def get(self, url: str, params=None):
        if params:
            # No pagination in this fixture.
            raise AssertionError(f"Unexpected pagination request: {url} {params}")
        self.calls.append(url)
        return _FakeResponse(url, self.pages[url])


def test_crawl_source_visits_all_explicit_seed_roots_even_cross_prefix():
    source = {
        "category": "Crystals",
        "path": "/en/timxtal/",
        "extra_paths": ["/en/timxtalmhz/", "/en/timkhz/"],
    }
    pages = {
        "https://www.spezial.com/en/timxtal/": "<html><h1>Crystals</h1></html>",
        "https://www.spezial.com/en/timxtalmhz/": "<html><h1>MHz Crystals</h1></html>",
        "https://www.spezial.com/en/timkhz/": "<html><h1>kHz Crystals</h1></html>",
    }
    client = _FakeClient(pages)

    rows = asyncio.run(
        crawl_source(
            client,
            source,
            discover_descendants=True,
            max_child_depth=3,
            max_listing_pages=10,
        )
    )

    assert rows == []
    assert set(client.calls) == set(pages)


def test_descendant_discovery_can_continue_beyond_one_level():
    source = {"category": "Example", "path": "/en/example/"}
    pages = {
        "https://www.spezial.com/en/example/": """
            <html><h1>Example</h1>
            <a href="/en/example-child/">Child</a></html>
        """,
        "https://www.spezial.com/en/example-child/": """
            <html><h1>Child</h1>
            <a href="/en/example-child-grand/">Grandchild</a></html>
        """,
        "https://www.spezial.com/en/example-child-grand/": """
            <html><h1>Grandchild</h1></html>
        """,
    }
    client = _FakeClient(pages)

    asyncio.run(
        crawl_source(
            client,
            source,
            discover_descendants=True,
            max_child_depth=3,
            max_listing_pages=10,
        )
    )

    assert "https://www.spezial.com/en/example-child-grand/" in client.calls
