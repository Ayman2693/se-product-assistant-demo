from app.services.evidence_service import _document_type, _is_document_link


def test_document_classifier():
    assert _document_type("MAYA-W2 data sheet", "https://x/a.pdf") == "datasheet"
    assert _document_type("Hardware Integration Manual", "https://x/b.pdf") == "integration_manual"
    assert _document_type("User Guide", "https://x/c.pdf") == "user_guide"


def test_document_detection():
    assert _is_document_link("Data sheet", "https://example.com/file.pdf")
    assert _is_document_link("Integration manual", "https://example.com/docs/manual")
    assert not _is_document_link("Request item", "https://example.com/request")
