import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.catalog_sources import CATALOG_BASE, CATALOG_SOURCES, source_seed_paths
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

def _normalized_page_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if not path.endswith("/"):
        path += "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _source_prefix(path: str) -> str:
    """
    Convert a configured catalog landing path into a safe descendant prefix.

    Examples:
      /en/sbc/        -> /en/sbc
      /en/com/        -> /en/com
      /en/passivecap/ -> /en/passivecap

    This intentionally allows:
      /en/sbc-picoitx/
      /en/com-smarc/
      /en/passivecaptantal/

    while excluding unrelated navigation branches.
    """
    return (urlparse(path).path or "/").rstrip("/")


def discover_child_listing_urls(
    html: str,
    *,
    current_url: str,
    root_path: str,
) -> list[str]:
    """
    Discover category/sub-category pages below one configured SE catalog source.

    Product detail URLs (-p1234) are excluded because parse_listing() already
    extracts those as products. Query-only pagination links are also excluded.
    """
    soup = BeautifulSoup(html, "html.parser")
    prefix = _source_prefix(root_path)
    current_normalized = _normalized_page_url(current_url)

    found: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = urljoin(current_url, a["href"])
        parsed = urlparse(href)

        if parsed.netloc and parsed.netloc.lower() != urlparse(CATALOG_BASE).netloc.lower():
            continue

        path = parsed.path or ""
        if not path.startswith("/en/"):
            continue

        # Stay strictly inside the configured source family.
        if not path.rstrip("/").startswith(prefix):
            continue

        if PRODUCT_PATH_RE.search(path):
            continue

        normalized = _normalized_page_url(href)
        if normalized == current_normalized:
            continue

        # Avoid non-catalog utility/document fragments that happen to share a prefix.
        label = _clean(a.get_text(" ", strip=True)).lower()
        if label in {
            "to the product",
            "to the documents",
            "request item",
            "add to favorites",
            "contact",
            "login",
        }:
            continue

        found.add(normalized)

    return sorted(found)


def _listing_label(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    label = _clean(h1.get_text(" ", strip=True)) if h1 else ""
    return label or fallback


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

def parse_listing(
    html: str,
    category: str,
    page_url: str,
    *,
    listing_label: str | None = None,
) -> tuple[list[ImportedProduct], int]:
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
        if listing_label and listing_label.lower() != category.lower():
            tags.append(listing_label)
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

async def crawl_source(
    client: httpx.AsyncClient,
    source: dict,
    max_pages: int | None = None,
    *,
    discover_descendants: bool = True,
    max_child_depth: int = 3,
    max_listing_pages: int = 100,
) -> list[ImportedProduct]:
    """
    Crawl one canonical SE product source, including explicit listing seeds.

    Coverage strategy:
      configured root + explicit extra listing roots
      -> descendant category pages
      -> pagination
      -> product cards

    Each seed keeps its own safe descendant prefix. This matters for shop trees
    whose child URL does not share the parent's prefix, e.g.:

      /en/timxtal/  -> /en/timkhz/

    /en/timkhz/ is therefore configured as an explicit seed for Crystals.

    Safety:
      - same SE host only
      - product detail links are never queued as category pages
      - visited URL de-duplication
      - maximum descendant depth
      - maximum listing/category-page budget
      - pagination capped at 100 pages per listing
    """
    seeds = source_seed_paths(source)

    # Queue: (listing URL, depth below its seed, seed root path).
    queue: list[tuple[str, int, str]] = [
        (
            _normalized_page_url(urljoin(CATALOG_BASE, seed_path)),
            0,
            seed_path,
        )
        for seed_path in seeds
    ]

    visited: set[str] = set()
    queued: set[str] = {item[0] for item in queue}
    products: list[ImportedProduct] = []

    while queue and len(visited) < max_listing_pages:
        current, depth, family_root_path = queue.pop(0)
        queued.discard(current)

        normalized = _normalized_page_url(current)
        if normalized in visited:
            continue
        visited.add(normalized)

        response = await client.get(current)
        response.raise_for_status()

        label = _listing_label(response.text, source["category"])
        first, detected_pages = parse_listing(
            response.text,
            source["category"],
            str(response.url),
            listing_label=label,
        )
        products.extend(first)

        if discover_descendants and depth < max_child_depth:
            for child in discover_child_listing_urls(
                response.text,
                current_url=str(response.url),
                root_path=family_root_path,
            ):
                if child not in visited and child not in queued:
                    queue.append((child, depth + 1, family_root_path))
                    queued.add(child)

        pages = detected_pages if max_pages is None else min(detected_pages, max_pages)

        # A malformed/navigation page must never explode into an unbounded
        # number of accidental pagination requests.
        pages = min(pages, 100)

        for page in range(2, pages + 1):
            paged = await client.get(current, params={"page": page})
            paged.raise_for_status()
            rows, _ = parse_listing(
                paged.text,
                source["category"],
                str(paged.url),
                listing_label=label,
            )
            products.extend(rows)

    dedup: dict[str, ImportedProduct] = {}
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
    discover_descendants: bool = True,
    max_concurrency: int = 3,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    """
    Import configured SE catalog sources.

    Network crawling is concurrent with a deliberately small concurrency
    (default 3) so the sync is much faster without aggressively loading
    spezial.com. Database writes remain sequential through one SQLAlchemy
    session.

    progress_callback receives a small state dict after every completed
    source, allowing /api/catalog/sync-status to show real progress.
    """
    selected = CATALOG_SOURCES
    if source_filter:
        needle = source_filter.strip().lower()
        selected = [
            x for x in selected
            if needle in x["category"].lower()
        ]
    if limit_sources is not None:
        selected = selected[:limit_sources]

    imported = 0
    failed: list[dict] = []
    source_counts: dict[str, int] = {}
    completed = 0

    timeout = httpx.Timeout(30.0, connect=15.0)
    headers = {"User-Agent": "SE-Product-Assistant/0.3 (+internal catalog sync)"}
    semaphore = asyncio.Semaphore(max(1, min(max_concurrency, 4)))

    if progress_callback:
        progress_callback({
            "sources_requested": len(selected),
            "sources_completed": 0,
            "sources_succeeded": 0,
            "products_seen": 0,
            "current_source": None,
            "failed": [],
        })

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
    ) as client:

        async def fetch_source(source: dict):
            async with semaphore:
                try:
                    rows = await crawl_source(
                        client,
                        source,
                        max_pages=max_pages,
                        discover_descendants=discover_descendants,
                    )
                    return source, rows, None
                except Exception as exc:
                    return source, [], str(exc)

        tasks = [
            asyncio.create_task(fetch_source(source))
            for source in selected
        ]

        for future in asyncio.as_completed(tasks):
            source, rows, error = await future
            completed += 1

            if error is not None:
                failed.append({
                    "source": source["category"],
                    "error": error,
                })
            else:
                try:
                    for row in rows:
                        upsert_product(db, row)
                    db.commit()
                    imported += len(rows)
                    source_counts[source["category"]] = len(rows)
                except Exception as exc:
                    db.rollback()
                    failed.append({
                        "source": source["category"],
                        "error": str(exc),
                    })

            if progress_callback:
                progress_callback({
                    "sources_requested": len(selected),
                    "sources_completed": completed,
                    "sources_succeeded": len(source_counts),
                    "products_seen": imported,
                    "current_source": source["category"],
                    "failed": list(failed),
                })

    return {
        "sources_requested": len(selected),
        "sources_completed": completed,
        "sources_succeeded": len(source_counts),
        "products_seen": imported,
        "source_counts": source_counts,
        "failed": failed,
        "recursive_discovery": discover_descendants,
        "max_concurrency": max(1, min(max_concurrency, 4)),
    }

