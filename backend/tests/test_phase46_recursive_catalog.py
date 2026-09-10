from app.services.catalog_importer import discover_child_listing_urls


def test_sbc_child_listing_discovery():
    html = """
    <html><body>
      <a href="/en/sbc/">Single Board Computer</a>
      <a href="/en/sbc-picoitx/">PicoITX</a>
      <a href="/en/sbc-35/">3.5&quot; SBC</a>
      <a href="/en/example-p1234/">Product</a>
      <a href="/en/com/">Computer on Modules</a>
    </body></html>
    """
    urls = discover_child_listing_urls(
        html,
        current_url="https://www.spezial.com/en/sbc/",
        root_path="/en/sbc/",
    )
    assert "https://www.spezial.com/en/sbc-picoitx/" in urls
    assert "https://www.spezial.com/en/sbc-35/" in urls
    assert not any("-p1234" in url for url in urls)
    assert not any("/en/com/" in url for url in urls)


def test_capacitor_child_listing_discovery_without_hyphen():
    html = """
    <a href="/en/passivecaptantal/">Tantalum</a>
    <a href="/en/passivecapfilm/">Film</a>
    """
    urls = discover_child_listing_urls(
        html,
        current_url="https://www.spezial.com/en/passivecap/",
        root_path="/en/passivecap/",
    )
    assert "https://www.spezial.com/en/passivecaptantal/" in urls
    assert "https://www.spezial.com/en/passivecapfilm/" in urls
