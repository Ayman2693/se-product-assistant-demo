from app.services.evidence_service import (
    _chunk_page,
    _document_type,
)


def test_productsummary_filename_classifier():
    assert (
        _document_type(
            "MAYA-W2_ProductSummary_UBX-21047385.pdf",
            "https://content.u-blox.com/MAYA-W2_ProductSummary_UBX-21047385.pdf",
        )
        == "product_summary"
    )


def test_chunker_preserves_short_text():
    text = "Wi-Fi 6 host-based module with Bluetooth 5.3."
    assert _chunk_page(text) == [text]


def test_chunker_splits_long_text():
    text = ("Wi-Fi 6 and Bluetooth 5.3. " * 300).strip()
    chunks = _chunk_page(text)
    assert len(chunks) > 1
    assert all(len(c) <= 2800 for c in chunks)
