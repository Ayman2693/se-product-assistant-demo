import json
import re
from io import BytesIO
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models import (
    Product,
    ProductDocument,
    ProductDocumentChunk,
    ProductEvidence,
    ProductEvidenceLocation,
)


def _json(value: str | None, fallback):
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _status_for_catalog_value(value) -> tuple[str, float]:
    if value in (None, "", [], {}):
        return "not_verified", 0.0
    # Values extracted from a short catalog description are useful evidence,
    # but they are not equivalent to a datasheet verification.
    return "inferred", 0.80


def _add_catalog_evidence(
    db: Session,
    product: Product,
    *,
    field_name: str,
    value,
    normalized_value: str | None = None,
    status: str | None = None,
    confidence: float | None = None,
):
    if value in (None, "", [], {}):
        return

    if status is None or confidence is None:
        default_status, default_confidence = _status_for_catalog_value(value)
        status = status or default_status
        confidence = default_confidence if confidence is None else confidence

    db.add(
        ProductEvidence(
            product_id=product.id,
            field_name=field_name,
            value_text=str(value),
            normalized_value=normalized_value if normalized_value is not None else str(value),
            verification_status=status,
            source_type="catalog_description",
            source_url=product.product_url or "",
            source_title=f"{product.part_number} — SE catalog",
            evidence_text=product.description or "",
            confidence=float(confidence),
        )
    )


def seed_catalog_evidence_for_product(db: Session, product: Product) -> int:
    # Rebuild only the catalog-derived layer. Future datasheet evidence is preserved.
    db.query(ProductEvidence).filter(
        ProductEvidence.product_id == product.id,
        ProductEvidence.source_type == "catalog_description",
    ).delete(synchronize_session=False)

    before = db.query(ProductEvidence).filter(
        ProductEvidence.product_id == product.id
    ).count()

    f = product.features

    # Direct catalog identity fields.
    _add_catalog_evidence(
        db, product,
        field_name="manufacturer",
        value=product.manufacturer,
        status="verified",
        confidence=1.0,
    )
    _add_catalog_evidence(
        db, product,
        field_name="category",
        value=product.category,
        status="verified",
        confidence=1.0,
    )

    if f:
        for tech in _json(f.technologies_json, []):
            normalized_tech = str(tech).lower()
            # "antenna" is a product feature, not a technology.
            # Preserve the rest of the catalog taxonomy such as sensor,
            # storage, display and timing for future assistant domains.
            if normalized_tech == "antenna":
                continue
            _add_catalog_evidence(
                db, product,
                field_name="technology",
                value=tech,
                normalized_value=normalized_tech,
            )

        mapping = {
            "cellular_class": f.cellular_class,
            "region": f.region,
            "has_gnss": f.has_gnss,
            "gnss_precision": f.gnss_precision,
            "wifi_generation": f.wifi_generation,
            "has_bluetooth": f.has_bluetooth,
            "architecture": f.architecture,
            "antenna": f.antenna,
            "form_factor": f.form_factor,
            "temperature_min": f.temperature_min,
            "temperature_max": f.temperature_max,
        }
        for field_name, value in mapping.items():
            _add_catalog_evidence(
                db,
                product,
                field_name=field_name,
                value=value,
            )

        for cert in _json(f.certifications_json, []):
            _add_catalog_evidence(
                db,
                product,
                field_name="certification",
                value=cert,
            )

        raw = _json(f.raw_features_json, {})
        if raw.get("low_power_positive") is True:
            _add_catalog_evidence(
                db,
                product,
                field_name="low_power",
                value=True,
                normalized_value="true",
                status="inferred",
                confidence=0.75,
            )
        elif raw.get("low_power_negative") is True:
            _add_catalog_evidence(
                db,
                product,
                field_name="low_power",
                value=False,
                normalized_value="false",
                status="inferred",
                confidence=0.90,
            )

    if product.lifecycle and "not verified" not in product.lifecycle.lower():
        _add_catalog_evidence(
            db,
            product,
            field_name="lifecycle",
            value=product.lifecycle,
            status="inferred",
            confidence=0.70,
        )

    if (
        product.availability
        and "check live" not in product.availability.lower()
        and "not verified" not in product.availability.lower()
    ):
        _add_catalog_evidence(
            db,
            product,
            field_name="availability",
            value=product.availability,
            status="inferred",
            confidence=0.70,
        )

    db.flush()

    after = db.query(ProductEvidence).filter(
        ProductEvidence.product_id == product.id
    ).count()
    return max(0, after - before)


def seed_catalog_evidence(db: Session, limit: int | None = None) -> dict:
    query = db.query(Product).order_by(Product.id)
    if limit is not None:
        query = query.limit(limit)

    products = query.all()
    records = 0
    for product in products:
        records += seed_catalog_evidence_for_product(db, product)

    db.commit()
    return {
        "products_processed": len(products),
        "catalog_evidence_records": db.query(ProductEvidence).filter(
            ProductEvidence.source_type == "catalog_description"
        ).count(),
        "new_records_in_run": records,
    }


def _document_type(title: str, url: str) -> str:
    text = f"{title} {url}".lower()
    if "integration manual" in text or "hardware integration" in text:
        return "integration_manual"
    if "datasheet" in text or "data sheet" in text:
        return "datasheet"
    if "user guide" in text or "user manual" in text:
        return "user_guide"
    if "product summary" in text or "productsummary" in text or "product-summary" in text:
        return "product_summary"
    if "certificate" in text or "certification" in text or "declaration" in text:
        return "certification"
    if "release note" in text:
        return "release_notes"
    return "other"


def _is_document_link(title: str, href: str) -> bool:
    text = f"{title} {href}".lower()
    path = urlparse(href).path.lower()

    if path.endswith(".pdf"):
        return True

    keywords = [
        "datasheet",
        "data-sheet",
        "integration-manual",
        "integration manual",
        "user-guide",
        "user guide",
        "product-summary",
        "product summary",
        "certificate",
        "certification",
        "declaration",
        "release-note",
        "release note",
    ]
    return any(k in text for k in keywords)


async def discover_documents_for_product(
    db: Session,
    client: httpx.AsyncClient,
    product: Product,
) -> int:
    if not product.product_url:
        return 0

    response = await client.get(product.product_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    discovered: dict[str, tuple[str, str]] = {}

    for anchor in soup.find_all("a", href=True):
        title = _clean(anchor.get_text(" ", strip=True))
        href = urljoin(str(response.url), anchor["href"])

        if not href.startswith(("http://", "https://")):
            continue
        if not _is_document_link(title, href):
            continue

        if not title:
            title = urlparse(href).path.rsplit("/", 1)[-1] or "Document"

        discovered[href] = (title, _document_type(title, href))

    added = 0
    for url, (title, doc_type) in discovered.items():
        existing = db.query(ProductDocument).filter(
            ProductDocument.product_id == product.id,
            ProductDocument.url == url,
        ).first()

        if existing:
            existing.title = title
            existing.document_type = doc_type
            existing.last_checked_at = datetime.utcnow()
            existing.status = "discovered"
            continue

        db.add(
            ProductDocument(
                product_id=product.id,
                document_type=doc_type,
                title=title,
                url=url,
                source_page_url=product.product_url,
                mime_type="application/pdf" if urlparse(url).path.lower().endswith(".pdf") else None,
                is_primary=doc_type in {"datasheet", "integration_manual", "product_summary"},
                status="discovered",
            )
        )
        added += 1

    db.flush()
    return added


async def discover_documents(
    db: Session,
    *,
    product_id: int | None = None,
    limit: int | None = None,
) -> dict:
    query = db.query(Product).filter(Product.product_url != "").order_by(Product.id)

    if product_id is not None:
        query = query.filter(Product.id == product_id)
    if limit is not None:
        query = query.limit(limit)

    products = query.all()
    added = 0
    failures: list[dict] = []

    timeout = httpx.Timeout(25.0, connect=10.0)
    headers = {
        "User-Agent": "SE-Product-Assistant/0.4 (+document discovery)"
    }

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
    ) as client:
        for product in products:
            try:
                added += await discover_documents_for_product(
                    db, client, product
                )
                db.commit()
            except Exception as exc:
                db.rollback()
                failures.append({
                    "product_id": product.id,
                    "part_number": product.part_number,
                    "error": str(exc),
                })

    return {
        "products_checked": len(products),
        "new_documents": added,
        "total_documents": db.query(ProductDocument).count(),
        "failures": failures,
    }


MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
CHUNK_SIZE = 2600
CHUNK_OVERLAP = 250


def _normalize_pdf_text(text: str | None) -> str:
    # PDF text extraction often returns typographic minus/dash characters.
    # Normalize them before rule-based engineering extraction.
    text = text or ""
    text = (
        text.replace("\u2212", "-")   # mathematical minus: −40
            .replace("\u2013", "-")  # en dash
            .replace("\u2014", "-")  # em dash
            .replace("\u00a0", " ")  # non-breaking space
    )
    return text


def _chunk_page(text: str) -> list[str]:
    text = _normalize_pdf_text(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []

    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE)

        if end < len(text):
            candidate = text[start:end]
            split_at = max(
                candidate.rfind("\n"),
                candidate.rfind(". "),
                candidate.rfind("; "),
            )
            if split_at > int(CHUNK_SIZE * 0.60):
                end = start + split_at + 1

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= len(text):
            break
        start = max(start + 1, end - CHUNK_OVERLAP)

    return chunks


def _snippet(text: str, start: int, end: int, radius: int = 180) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    quote = re.sub(r"\s+", " ", text[left:right]).strip()
    return quote[:700]


def _doc_source_type(document: ProductDocument) -> str:
    value = (document.document_type or "other").strip().lower()
    allowed = {
        "datasheet",
        "integration_manual",
        "user_guide",
        "product_summary",
        "certification",
        "release_notes",
    }
    return value if value in allowed else "other"


def _record_verified(
    db: Session,
    *,
    product: Product,
    document: ProductDocument,
    chunk: ProductDocumentChunk,
    field_name: str,
    value_text: str,
    normalized_value: str,
    quote: str,
    confidence: float = 0.97,
) -> bool:
    existing = (
        db.query(ProductEvidence)
        .filter(
            ProductEvidence.product_id == product.id,
            ProductEvidence.document_id == document.id,
            ProductEvidence.field_name == field_name,
            ProductEvidence.normalized_value == normalized_value,
            ProductEvidence.verification_status == "verified",
        )
        .first()
    )
    if existing:
        return False

    evidence = ProductEvidence(
        product_id=product.id,
        document_id=document.id,
        field_name=field_name,
        value_text=value_text,
        normalized_value=normalized_value,
        verification_status="verified",
        source_type=_doc_source_type(document),
        source_url=document.url or "",
        source_title=f"{document.title} — page {chunk.page_number}",
        evidence_text=quote,
        confidence=confidence,
    )
    db.add(evidence)
    db.flush()

    db.add(
        ProductEvidenceLocation(
            evidence_id=evidence.id,
            chunk_id=chunk.id,
            page_number=chunk.page_number,
            quote=quote,
        )
    )
    return True


def _extract_verified_from_chunk(
    db: Session,
    *,
    product: Product,
    document: ProductDocument,
    chunk: ProductDocumentChunk,
) -> int:
    text = chunk.text
    created = 0

    def add_match(
        field_name: str,
        value_text: str,
        normalized_value: str,
        match: re.Match,
        confidence: float = 0.97,
    ):
        nonlocal created
        if _record_verified(
            db,
            product=product,
            document=document,
            chunk=chunk,
            field_name=field_name,
            value_text=value_text,
            normalized_value=normalized_value,
            quote=_snippet(text, match.start(), match.end()),
            confidence=confidence,
        ):
            created += 1

    # Technologies — explicit wording only.
    tech_patterns = [
        ("wifi", re.compile(r"\bWi-?Fi\b|IEEE\s*802\.11", re.I)),
        ("bluetooth", re.compile(r"\bBluetooth\b|\bBLE\b", re.I)),
        ("gnss", re.compile(r"\bGNSS\b|\bGPS\b|\bGalileo\b|\bGLONASS\b|\bBeiDou\b", re.I)),
        ("cellular", re.compile(r"\bLTE\b|\b5G\b|\bNB-?IoT\b|\bLTE-?M\b", re.I)),
    ]
    for normalized, pattern in tech_patterns:
        m = pattern.search(text)
        if m:
            add_match("technology", normalized, normalized, m, 0.98)

    # Wi-Fi generation. Check 6E before 6.
    wifi_patterns = [
        ("6E", re.compile(r"\bWi-?Fi\s*6E\b", re.I)),
        ("6", re.compile(r"\bWi-?Fi\s*6\b|\b802\.11ax\b", re.I)),
        ("5", re.compile(r"\bWi-?Fi\s*5\b|\b802\.11ac\b", re.I)),
        ("4", re.compile(r"\bWi-?Fi\s*4\b|\b802\.11n\b", re.I)),
    ]
    for normalized, pattern in wifi_patterns:
        m = pattern.search(text)
        if m:
            add_match("wifi_generation", f"Wi-Fi {normalized}", normalized, m)
            break

    # Bluetooth version.
    # Do not confuse electrical interface wording such as "Bluetooth 4-wire UART"
    # with Bluetooth version 4.
    bt = None
    for candidate in re.finditer(
        r"\bBluetooth(?:\s+Low\s+Energy|\s+LE)?\s*(?:version\s*|v\s*)?([4-6](?:\.\d+)?)\b",
        text,
        re.I,
    ):
        suffix = text[candidate.end():candidate.end() + 20]
        if re.match(r"\s*[- ]?wire\b", suffix, re.I):
            continue
        bt = candidate
        break

    if bt:
        add_match(
            "bluetooth_version",
            f"Bluetooth {bt.group(1)}",
            bt.group(1),
            bt,
        )

    # Architecture — conservative exact language.
    architecture_patterns = [
        ("host", re.compile(r"\bhost[- ]based\b", re.I)),
        ("open", re.compile(r"\bopen[- ]?cpu\b", re.I)),
        ("uconnect", re.compile(r"\bu-?connectXpress\b", re.I)),
    ]
    for normalized, pattern in architecture_patterns:
        m = pattern.search(text)
        if m:
            add_match("architecture", normalized, normalized, m)
            break

    # Host interfaces can be multi-valued.
    interface_patterns = [
        ("sdio", re.compile(r"\bSDIO\b", re.I)),
        ("pcie", re.compile(r"\bPCIe\b|\bPCI\s+Express\b", re.I)),
        ("usb", re.compile(r"\bUSB\b", re.I)),
        ("uart", re.compile(r"\bUART\b", re.I)),
        ("spi", re.compile(r"\bSPI\b", re.I)),
        ("i2c", re.compile(r"\bI2C\b|\bI²C\b", re.I)),
    ]
    for normalized, pattern in interface_patterns:
        m = pattern.search(text)
        if m:
            add_match("interface", normalized.upper(), normalized, m, 0.96)

    # Cellular classes.
    cellular_patterns = [
        ("5G RedCap", re.compile(r"\b5G\s+RedCap\b|\bNR[- ]?RedCap\b", re.I)),
        ("Cat 1bis", re.compile(r"\bCat(?:egory)?\s*\.?\s*1\s*bis\b|\bCat\.?1bis\b", re.I)),
        ("Cat 4", re.compile(r"\bCat(?:egory)?\s*\.?\s*4\b|\bCat\.?4\b", re.I)),
        ("LTE-M", re.compile(r"\bLTE-?M\b|\bCat-?M1\b", re.I)),
        ("NB-IoT", re.compile(r"\bNB-?IoT\b", re.I)),
    ]
    for normalized, pattern in cellular_patterns:
        m = pattern.search(text)
        if m:
            add_match("cellular_class", normalized, normalized, m)

    # GNSS capability / precision / dual band.
    rtk = re.search(
        r"\bRTK\b|centimeter[- ]level|centimetre[- ]level|centimeter accuracy|centimetre accuracy",
        text,
        re.I,
    )
    if rtk:
        add_match("gnss_precision", "centimeter / RTK", "cm", rtk, 0.98)

    dual = re.search(
        r"\bL1\s*(?:\+|and|/)\s*L5\b|dual[- ](?:band|frequency)\s+GNSS",
        text,
        re.I,
    )
    if dual:
        add_match("gnss_dual_band", "L1 + L5", "true", dual, 0.98)

    # Mechanical form-factor terms that are explicit and unambiguous.
    form_patterns = [
        ("Mini PCIe", re.compile(r"\bMini\s+PCIe\b", re.I)),
        ("M.2", re.compile(r"\bM\.2\b", re.I)),
        ("LGA", re.compile(r"\bLGA\b", re.I)),
        ("LCC", re.compile(r"\bLCC\b", re.I)),
    ]
    for normalized, pattern in form_patterns:
        m = pattern.search(text)
        if m:
            add_match("form_factor", normalized, normalized, m, 0.96)

    # Temperature range only when the range is written explicitly.
    temp = re.search(
        r"(-?\d{1,3})\s*°?\s*C\s*(?:to|…|–|-)\s*\+?(-?\d{1,3})\s*°?\s*C",
        text,
        re.I,
    )
    if temp:
        lo = int(temp.group(1))
        hi = int(temp.group(2))
        if -60 <= lo <= 150 and -60 <= hi <= 180 and lo < hi:
            add_match("temperature_min", f"{lo} °C", str(lo), temp, 0.95)
            add_match("temperature_max", f"{hi} °C", str(hi), temp, 0.95)

    # Intentionally NOT verifying antenna variant or exact dimensions here.
    # Family product summaries often describe multiple SKUs; variant-specific
    # verification will be added only after table-aware extraction.

    return created


async def ingest_document(
    db: Session,
    client: httpx.AsyncClient,
    document: ProductDocument,
) -> dict:
    if not document.url.startswith(("http://", "https://")):
        raise ValueError("Only HTTP(S) document URLs are supported")

    response = await client.get(document.url)
    response.raise_for_status()

    content = response.content
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError(
            f"Document is too large ({len(content)} bytes; max {MAX_DOCUMENT_BYTES})"
        )

    if not content.startswith(b"%PDF"):
        raise ValueError("Document is not a PDF")

    # Re-classify already discovered records such as ProductSummary filenames.
    detected_type = _document_type(document.title or "", document.url or "")
    if detected_type != "other":
        document.document_type = detected_type
        if detected_type in {"datasheet", "integration_manual", "product_summary"}:
            document.is_primary = True

    # Clear only this document's prior parsed layer so re-runs are deterministic.
    # Bulk deletes bypass ORM cascades, therefore provenance locations must be
    # removed explicitly before deleting evidence/chunks.
    prior_evidence_ids = [
        row[0]
        for row in db.query(ProductEvidence.id).filter(
            ProductEvidence.document_id == document.id,
            ProductEvidence.source_type != "catalog_description",
        ).all()
    ]

    if prior_evidence_ids:
        db.query(ProductEvidenceLocation).filter(
            ProductEvidenceLocation.evidence_id.in_(prior_evidence_ids)
        ).delete(synchronize_session=False)

    prior_chunk_ids = [
        row[0]
        for row in db.query(ProductDocumentChunk.id).filter(
            ProductDocumentChunk.document_id == document.id
        ).all()
    ]

    if prior_chunk_ids:
        db.query(ProductEvidenceLocation).filter(
            ProductEvidenceLocation.chunk_id.in_(prior_chunk_ids)
        ).delete(synchronize_session=False)

    db.query(ProductEvidence).filter(
        ProductEvidence.document_id == document.id,
        ProductEvidence.source_type != "catalog_description",
    ).delete(synchronize_session=False)

    db.query(ProductDocumentChunk).filter(
        ProductDocumentChunk.document_id == document.id
    ).delete(synchronize_session=False)
    db.flush()

    reader = PdfReader(BytesIO(content))
    chunk_count = 0
    verified_count = 0
    pages_with_text = 0

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""

        if not page_text.strip():
            continue

        pages_with_text += 1
        for chunk_index, chunk_text in enumerate(_chunk_page(page_text)):
            chunk = ProductDocumentChunk(
                document_id=document.id,
                page_number=page_number,
                chunk_index=chunk_index,
                text=chunk_text,
                char_count=len(chunk_text),
            )
            db.add(chunk)
            db.flush()
            chunk_count += 1

            verified_count += _extract_verified_from_chunk(
                db,
                product=document.product,
                document=document,
                chunk=chunk,
            )

    if pages_with_text == 0:
        document.status = "no_text"
    else:
        document.status = "parsed"

    document.last_checked_at = datetime.utcnow()
    db.commit()

    return {
        "document_id": document.id,
        "product_id": document.product_id,
        "title": document.title,
        "document_type": document.document_type,
        "status": document.status,
        "pages_total": len(reader.pages),
        "pages_with_text": pages_with_text,
        "chunks_created": chunk_count,
        "verified_evidence_created": verified_count,
    }


async def ingest_documents(
    db: Session,
    *,
    document_id: int | None = None,
    product_id: int | None = None,
    limit: int | None = None,
) -> dict:
    query = db.query(ProductDocument).order_by(ProductDocument.id)

    if document_id is not None:
        query = query.filter(ProductDocument.id == document_id)
    if product_id is not None:
        query = query.filter(ProductDocument.product_id == product_id)
    if limit is not None:
        query = query.limit(limit)

    documents = query.all()
    parsed = 0
    failed = 0
    chunks_created = 0
    verified_created = 0
    failures: list[dict] = []

    timeout = httpx.Timeout(45.0, connect=15.0)
    headers = {
        "User-Agent": "SE-Product-Assistant/0.4.2 (+document-ingestion)"
    }

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
    ) as client:
        for document in documents:
            try:
                result = await ingest_document(db, client, document)
                if result["status"] == "parsed":
                    parsed += 1
                else:
                    failed += 1
                chunks_created += result["chunks_created"]
                verified_created += result["verified_evidence_created"]
            except Exception as exc:
                db.rollback()
                try:
                    doc = db.get(ProductDocument, document.id)
                    if doc:
                        doc.status = "parse_failed"
                        doc.last_checked_at = datetime.utcnow()
                        db.commit()
                except Exception:
                    db.rollback()

                failed += 1
                failures.append(
                    {
                        "document_id": document.id,
                        "product_id": document.product_id,
                        "title": document.title,
                        "error": str(exc),
                    }
                )

    return {
        "documents_requested": len(documents),
        "documents_parsed": parsed,
        "documents_failed": failed,
        "chunks_created": chunks_created,
        "verified_evidence_created": verified_created,
        "failures": failures,
    }
