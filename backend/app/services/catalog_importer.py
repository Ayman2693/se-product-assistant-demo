import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.catalog_sources import CATALOG_BASE, CATALOG_SOURCES
from app.models import Product, ProductFeature
from app.services.feature_extractor import extract_features, feature_values_for_model

MANUFACTURER_ALIASES = {
    "amphenol": "Amphenol", "antenova": "Antenova", "cavli": "Cavli",
    "cml micro": "CML Micro", "conec": "CONEC", "congatec": "congatec",
    "degson": "Degson", "diamond systems": "Diamond Systems", "digi": "Digi",
    "ept": "ept", "finder": "Finder", "foresee": "Foresee", "harting": "Harting",
    "honeywell": "Honeywell", "hosonic": "Hosonic", "innodisk": "Innodisk",
    "kemet": "Kemet", "micro crystal": "Micro Crystal", "ortustech": "Ortustech",
    "provertha": "Provertha", "schaffner": "Schaffner", "schaltbau": "Schaltbau",
    "seco": "SECO", "sitime": "SiTime", "synzen": "SynZen", "taoglas": "Taoglas",
    "trasna": "Trasna", "u-blox": "u-blox", "ublox": "u-blox",
    "wima": "WIMA", "winstar": "Winstar", "xsens": "Xsens", "yageo": "YAGEO",
}

PRODUCT_PATH_RE = re.compile(r"/en/[^?#]*-p\d+/?$", re.I)

@dataclass
class ImportedProduct:
    part_number: str
    manufacturer: str
    category: str
    description: str
    product_url: str
    documents_url: str
    request_url: str
    availability: str
    tags: list[str]
    source_url: str

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def _manufacturer(text: str) -> str:
    t = text.lower()
    for key in sorted(MANUFACTURER_ALIASES, key=len, reverse=True):
        if key in t:
            return MANUFACTURER_ALIASES[key]
    # SE descriptions commonly begin "Manufacturer*..."
    head = _clean(text).split("*", 1)[0].strip()
    if 1 < len(head) < 40:
        return head
    return "SE Partner"

def _availability(text: str) -> str:
    patterns = [
        r"In Stock\.",
        r"Low availability\.",
        r"Currently not available",
        r"Orderable,\s*delivery time[^.]*\.?",
        r"Usually ships in \d+\s*to\s*\d+\s*days",
        r"Item expires",
    ]
    hits = []
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            hits.append(_clean(m.group(0)))
    return " · ".join(dict.fromkeys(hits)) if hits else "Check live SE page"

def _card_for_anchor(anchor):
    node = anchor
    for _ in range(10):
        if node is None:
            break
        text = _clean(node.get_text(" ", strip=True))
        if "Manufacturer Item No.:" in text and "Item number:" in text:
            return node
        node = node.parent
    return anchor.parent

def _max_page(soup: BeautifulSoup, current_url: str) -> int:
    max_page = 1
    for a in soup.find_all("a", href=True):
        label = _clean(a.get_text())
        if not label.isdigit():
            continue
        href = urljoin(current_url, a["href"])
        q = parse_qs(urlparse(href).query)
        if "page" in q:
            try:
                max_page = max(max_page, int(q["page"][0]))
            except (ValueError, TypeError):
                pass
        else:
            try:
                max_page = max(max_page, int(label))
            except ValueError:
                pass
    return max_page

def parse_listing(html: str, category: str, page_url: str) -> tuple[list[ImportedProduct], int]:
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, ImportedProduct] = {}

    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        if not PRODUCT_PATH_RE.search(urlparse(href).path):
            continue

        title = _clean(a.get_text(" ", strip=True))
        if not title or len(title) > 120:
            continue
        if title.lower() in {"to the product", "to the documents", "request item", "add to favorites"}:
            continue

        card = _card_for_anchor(a)
        card_text = _clean(card.get_text(" ", strip=True))
        if "Manufacturer Item No.:" not in card_text:
            continue

        # Prefer shop "Item number" as the canonical ordering code.
        item_match = re.search(r"Item number:\s*([A-Za-z0-9_.+/\-]+)", card_text, re.I)
        part_number = item_match.group(1) if item_match else title
        if len(part_number) < 2:
            continue

        manufacturer = _manufacturer(card_text)

        # Keep the useful product description and strip cart boilerplate.
        desc = card_text
        desc = re.split(r"Manufacturer Item No\.:", desc, maxsplit=1, flags=re.I)[0]
        if desc.lower().startswith(part_number.lower()):
            desc = desc[len(part_number):].strip(" *")
        desc = _clean(desc)

        documents_url = ""
        request_url = ""
        for x in card.find_all("a", href=True):
            txt = _clean(x.get_text()).lower()
            if "documents" in txt:
                documents_url = urljoin(page_url, x["href"])
            elif "request item" in txt:
                request_url = urljoin(page_url, x["href"])

        tags = [manufacturer, category]
        found[part_number.upper()] = ImportedProduct(
            part_number=part_number,
            manufacturer=manufacturer,
            category=category,
            description=desc,
            product_url=href,
            documents_url=documents_url or (href + "#hasDocuments"),
            request_url=request_url or (href + "#hasDocuments#requestItem"),
            availability=_availability(card_text),
            tags=tags,
            source_url=page_url,
        )

    return list(found.values()), _max_page(soup, page_url)

async def crawl_source(client: httpx.AsyncClient, source: dict, max_pages: int | None = None) -> list[ImportedProduct]:
    base_url = urljoin(CATALOG_BASE, source["path"])
    response = await client.get(base_url)
    response.raise_for_status()

    first, detected_pages = parse_listing(response.text, source["category"], str(response.url))
    pages = detected_pages if max_pages is None else min(detected_pages, max_pages)
    products = list(first)

    for page in range(2, pages + 1):
        response = await client.get(base_url, params={"page": page})
        response.raise_for_status()
        rows, _ = parse_listing(response.text, source["category"], str(response.url))
        products.extend(rows)

    dedup = {}
    for item in products:
        dedup[item.part_number.upper()] = item
    return list(dedup.values())

def upsert_product(db: Session, item: ImportedProduct) -> Product:
    product = db.query(Product).filter(Product.part_number == item.part_number).first()

    # IMPORTANT: manufacturer/category are NOT NULL in the database.
    # Populate all mandatory fields before the first flush/INSERT.
    values = {
        "manufacturer": item.manufacturer or "SE Partner",
        "category": item.category or "Uncategorized",
        "description": item.description or "",
        "tags_json": json.dumps(item.tags or [], ensure_ascii=False),
        "product_url": item.product_url or "",
        "availability": item.availability or "Check live SE page",
        "exact": True,
    }

    if product is None:
        product = Product(
            part_number=item.part_number,
            **values,
        )
        db.add(product)
        db.flush()
    else:
        for key, value in values.items():
            setattr(product, key, value)

    extracted = extract_features(
        part_number=item.part_number,
        manufacturer=item.manufacturer,
        category=item.category,
        description=item.description,
        tags=item.tags,
    )

    feature = product.features
    if feature is None:
        feature = ProductFeature(product=product)
        db.add(feature)

    for key, value in feature_values_for_model(extracted).items():
        setattr(feature, key, value)

    feature.documents_url = item.documents_url
    feature.request_url = item.request_url
    feature.source_category = item.category
    feature.source_url = item.source_url
    feature.imported_live = True

    return product

async def import_catalog(
    db: Session,
    *,
    source_filter: str | None = None,
    limit_sources: int | None = None,
    max_pages: int | None = None,
) -> dict:
    selected = CATALOG_SOURCES
    if source_filter:
        needle = source_filter.strip().lower()
        # Match human-readable category names, not arbitrary URL substrings.
        # Example: "--source LTE" should match LTE-related categories, but not "/filteracc/".
        selected = [
            x for x in selected
            if needle in x["category"].lower()
        ]
    if limit_sources is not None:
        selected = selected[:limit_sources]

    imported = 0
    failed = []
    source_counts = {}

    timeout = httpx.Timeout(30.0, connect=15.0)
    headers = {"User-Agent": "SE-Product-Assistant/0.2 (+internal catalog sync)"}

    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        for source in selected:
            try:
                rows = await crawl_source(client, source, max_pages=max_pages)
                for row in rows:
                    upsert_product(db, row)
                db.commit()
                imported += len(rows)
                source_counts[source["category"]] = len(rows)
            except Exception as exc:
                db.rollback()
                failed.append({"source": source["category"], "error": str(exc)})

    return {
        "sources_requested": len(selected),
        "sources_succeeded": len(source_counts),
        "products_seen": imported,
        "source_counts": source_counts,
        "failed": failed,
    }
