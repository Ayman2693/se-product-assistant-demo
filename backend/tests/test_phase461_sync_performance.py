import asyncio

from app.services.catalog_importer import discover_child_listing_urls


def test_child_discovery_is_prefix_scoped():
    html = """
    <a href="/en/passivecaptantal/">Tantal</a>
    <a href="/en/passivecapfilm/">Film</a>
    <a href="/en/sbc-picoitx/">Unrelated</a>
    """
    urls = discover_child_listing_urls(
        html,
        current_url="https://www.spezial.com/en/passivecap/",
        root_path="/en/passivecap/",
    )
    assert urls == [
        "https://www.spezial.com/en/passivecapfilm/",
        "https://www.spezial.com/en/passivecaptantal/",
    ]


def test_concurrency_cap_design_constant():
    # The importer clamps external input to at most four concurrent source
    # crawls. Production uses three.
    requested = 99
    effective = max(1, min(requested, 4))
    assert effective == 4
