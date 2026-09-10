import asyncio
import json
from datetime import datetime, timezone
import logging
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, contains_eager, joinedload
from sqlalchemy import or_

from app.catalog_sources import CATALOG_SOURCES
from app.db import SessionLocal, get_db
from app.models import Product, ProductFeature
from app.schemas import CatalogStatusResponse, MatchRequest, MatchResponse, ProductOut
from app.services.matcher import score_product
from app.services.catalog_importer import import_catalog
from app.services.evidence_service import seed_catalog_evidence
from app.services.evidence_matcher import (
    annotate_results_with_evidence,
    evidence_sort_key,
)


logger = logging.getLogger(__name__)

_GENERIC_CATEGORY_WORDS = {
    "sensor", "sensors",
    "module", "modules",
    "product", "products",
    "component", "components",
    "display", "displays",
    "solution", "solutions",
    "device", "devices",
}


def _text_has_any(terms: list[str]):
    """Broad SQL text predicate used only as a conservative pre-filter."""
    columns = (
        Product.part_number,
        Product.manufacturer,
        Product.category,
        Product.description,
        Product.tags_json,
    )
    clauses = []
    for term in terms:
        like = f"%{term}%"
        clauses.extend(column.ilike(like) for column in columns)
    return or_(*clauses) if clauses else None


def _category_prefilter_terms(category: str) -> list[str]:
    """
    Return specific category words for a SQL superset filter.

    The Python matcher remains authoritative. This pre-filter intentionally
    stays broader than _catalog_category_matches() so it cannot choose a
    winner or invent technical meaning.
    """
    words = re.findall(r"[a-z0-9]+", (category or "").lower())
    specific = [
        word
        for word in words
        if len(word) >= 3 and word not in _GENERIC_CATEGORY_WORDS
    ]
    if specific:
        return specific[:4]

    # "Capacitors" and similar one-word product classes should still narrow.
    return [word[:-1] if word.endswith("s") and len(word) > 4 else word for word in words[:2]]


def _technology_prefilter(technology: str):
    tech = (technology or "").lower()

    if tech == "wifi":
        return or_(
            ProductFeature.wifi_generation.is_not(None),
            ProductFeature.technologies_json.ilike("%wifi%"),
            _text_has_any(["wi-fi", "wifi", "wlan", "802.11"]),
        )

    if tech == "bluetooth":
        return or_(
            ProductFeature.has_bluetooth.is_(True),
            ProductFeature.technologies_json.ilike("%bluetooth%"),
            _text_has_any(["bluetooth", " ble ", "bt/ble"]),
        )

    if tech == "gnss":
        return or_(
            ProductFeature.has_gnss.is_(True),
            ProductFeature.technologies_json.ilike("%gnss%"),
            _text_has_any(["gnss", "gps", "rtk", "galileo", "glonass", "beidou"]),
        )

    if tech == "cellular":
        return or_(
            ProductFeature.cellular_class.is_not(None),
            ProductFeature.technologies_json.ilike("%cellular%"),
            _text_has_any(["cellular", "lte", "nb-iot", "nbiot", "redcap", "5g"]),
        )

    return None


def _candidate_query(db: Session, request: MatchRequest):
    """
    Build a conservative SQL pre-filter and eager-load Product.features.

    contains_eager() reuses the ProductFeature join for the one-to-one
    relationship, preventing the old N+1 lazy-load pattern.
    """
    query = (
        db.query(Product)
        .outerjoin(ProductFeature, ProductFeature.product_id == Product.id)
        .options(contains_eager(Product.features))
    )
    applied_filters = False

    if request.catalog_category:
        category_terms = _category_prefilter_terms(request.catalog_category)
        category_clause = _text_has_any(category_terms)
        if category_clause is not None:
            # Category intent is mandatory in score_product(). Search only
            # category text here, but with broad specific terms.
            clauses = [
                Product.category.ilike(f"%{term}%")
                for term in category_terms
            ]
            query = query.filter(or_(*clauses))
            applied_filters = True

    requested_technologies = list(request.technologies or [])
    if request.bluetooth_required and "bluetooth" not in requested_technologies:
        requested_technologies.append("bluetooth")

    for technology in requested_technologies:
        clause = _technology_prefilter(technology)
        if clause is not None:
            # Technologies are mandatory in score_product(), so AND across
            # requested technologies mirrors the existing matcher semantics.
            query = query.filter(clause)
            applied_filters = True

    return query, applied_filters


def _load_match_candidates(db: Session, request: MatchRequest) -> list[Product]:
    query, applied_filters = _candidate_query(db, request)
    candidates = query.all()

    # Correctness guard: if conservative SQL filtering unexpectedly finds
    # nothing, fall back to the complete catalog with eager-loaded features.
    # This protects against unusual legacy catalog wording.
    if not candidates and applied_filters:
        logger.warning(
            "Match SQL pre-filter returned zero rows; falling back to full catalog."
        )
        return db.query(Product).options(joinedload(Product.features)).all()

    return candidates


def _technical_evidence_pool(scored: list[tuple[Product, dict]], limit: int = 10):
    """
    Keep only products that can still enter the returned top-N.

    Evidence is only a tie-breaker after technical match_percent. Therefore
    products below the Nth technical score can never overtake the cutoff and
    do not need evidence queries. All products tied at the cutoff are kept.
    """
    if len(scored) <= limit:
        return scored

    ordered = sorted(
        scored,
        key=lambda item: item[1].get("match_percent", 0),
        reverse=True,
    )
    cutoff_score = ordered[limit - 1][1].get("match_percent", 0)
    return [
        item
        for item in ordered
        if item[1].get("match_percent", 0) >= cutoff_score
    ]


router = APIRouter(prefix="/api", tags=["products"])

_catalog_sync_task: asyncio.Task | None = None
_catalog_sync_state = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "products_seen": 0,
    "sources_succeeded": 0,
    "sources_completed": 0,
    "sources_requested": 0,
    "current_source": None,
    "failed": [],
    "error": None,
}


def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


async def _run_full_catalog_sync():
    _catalog_sync_state.update({
        "status": "running",
        "started_at": _utcnow_iso(),
        "finished_at": None,
        "products_seen": 0,
        "sources_succeeded": 0,
        "sources_completed": 0,
        "sources_requested": len(CATALOG_SOURCES),
        "current_source": None,
        "failed": [],
        "error": None,
    })

    def on_progress(progress: dict):
        _catalog_sync_state.update({
            "products_seen": progress.get("products_seen", 0),
            "sources_succeeded": progress.get("sources_succeeded", 0),
            "sources_completed": progress.get("sources_completed", 0),
            "sources_requested": progress.get("sources_requested", len(CATALOG_SOURCES)),
            "current_source": progress.get("current_source"),
            "failed": progress.get("failed", []),
        })

    db = SessionLocal()
    try:
        result = await import_catalog(
            db,
            discover_descendants=True,
            max_concurrency=3,
            progress_callback=on_progress,
        )

        # Evidence rebuild happens once, after the product crawl finishes.
        _catalog_sync_state["status"] = "rebuilding_evidence"
        _catalog_sync_state["current_source"] = None

        evidence = seed_catalog_evidence(db)

        _catalog_sync_state.update({
            "status": "completed",
            "finished_at": _utcnow_iso(),
            "products_seen": result.get("products_seen", 0),
            "sources_succeeded": result.get("sources_succeeded", 0),
            "sources_completed": result.get("sources_completed", 0),
            "sources_requested": result.get("sources_requested", 0),
            "failed": result.get("failed", []),
            "evidence": evidence,
        })
    except asyncio.CancelledError:
        _catalog_sync_state.update({
            "status": "cancelled",
            "finished_at": _utcnow_iso(),
            "current_source": None,
        })
        raise
    except Exception as exc:
        _catalog_sync_state.update({
            "status": "failed",
            "finished_at": _utcnow_iso(),
            "error": str(exc),
            "current_source": None,
        })
    finally:
        db.close()


@router.post("/catalog/sync")
async def start_full_catalog_sync():
    """
    Start a full recursive SE catalog refresh in the background.

    This is especially useful on Render Free, where shell/one-off jobs are
    unavailable. The app-level demo Basic Auth protects this endpoint when
    DEMO_PASSWORD is configured.
    """
    global _catalog_sync_task

    if _catalog_sync_task is not None and not _catalog_sync_task.done():
        return {
            **_catalog_sync_state,
            "message": "Catalog sync is already running.",
        }

    _catalog_sync_task = asyncio.create_task(_run_full_catalog_sync())
    return {
        **_catalog_sync_state,
        "status": "starting",
        "message": "Full recursive SE catalog sync started.",
    }


@router.get("/catalog/sync-status")
def full_catalog_sync_status():
    return dict(_catalog_sync_state)


@router.post("/catalog/sync-cancel")
async def cancel_full_catalog_sync():
    global _catalog_sync_task

    if _catalog_sync_task is None or _catalog_sync_task.done():
        return {
            **_catalog_sync_state,
            "message": "No catalog sync is currently running.",
        }

    _catalog_sync_task.cancel()
    try:
        await _catalog_sync_task
    except asyncio.CancelledError:
        pass

    return {
        **_catalog_sync_state,
        "message": "Catalog sync cancelled.",
    }


def _json(value, fallback):
    try:
        return json.loads(value or "")
    except Exception:
        return fallback

def serialize_features(f: ProductFeature | None):
    if not f:
        return None
    raw = _json(f.raw_features_json, {})
    return {
        "technologies": _json(f.technologies_json, []),
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
        "certifications": _json(f.certifications_json, []),
        "documents_url": f.documents_url or "",
        "request_url": f.request_url or "",
        "imported_live": bool(f.imported_live),
        "capacitance_uf": raw.get("capacitance_uf"),
        "capacitor_voltage_v": raw.get("capacitor_voltage_v"),
        "capacitor_tolerance_pct": raw.get("capacitor_tolerance_pct"),
        "capacitor_technology": raw.get("capacitor_technology"),
        "capacitor_mounting": raw.get("capacitor_mounting"),
        "capacitor_case_size": raw.get("capacitor_case_size"),
        "capacitor_esr_ohm": raw.get("capacitor_esr_ohm"),
        "capacitor_ripple_current_a": raw.get("capacitor_ripple_current_a"),
        "capacitor_lifetime_h": raw.get("capacitor_lifetime_h"),
        "capacitor_theoretical_energy_j": raw.get("capacitor_theoretical_energy_j"),
    }

def serialize_product(p: Product):
    return {
        "id": p.id,
        "part_number": p.part_number,
        "manufacturer": p.manufacturer,
        "category": p.category,
        "description": p.description or "",
        "tags": _json(p.tags_json, []),
        "product_url": p.product_url or "",
        "lifecycle": p.lifecycle or "",
        "availability": p.availability or "",
        "features": serialize_features(p.features),
    }

@router.get("/catalog/status", response_model=CatalogStatusResponse)
def catalog_status(db: Session = Depends(get_db)):
    total = db.query(Product).count()
    structured = db.query(ProductFeature).count()
    live = db.query(ProductFeature).filter(ProductFeature.imported_live.is_(True)).count()
    return {
        "total_products": total,
        "structured_products": structured,
        "live_imported_products": live,
        "catalog_sections_configured": len(CATALOG_SOURCES),
    }

@router.get("/products", response_model=list[ProductOut])
def list_products(
    q: str | None = Query(default=None),
    manufacturer: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if manufacturer:
        query = query.filter(Product.manufacturer == manufacturer)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Product.part_number.ilike(like),
            Product.manufacturer.ilike(like),
            Product.category.ilike(like),
            Product.description.ilike(like),
        ))
    rows = query.order_by(Product.manufacturer, Product.part_number).limit(limit).all()
    return [serialize_product(p) for p in rows]

@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(p)

@router.post("/match", response_model=MatchResponse)
def match_products(r: MatchRequest, db: Session = Depends(get_db)):
    started = time.perf_counter()

    # Phase 4.7.5:
    # 1) conservative SQL pre-filter
    # 2) eager-load Product.features in the same query
    # 3) technical scoring remains authoritative
    candidates = _load_match_candidates(db, r)

    scored: list[tuple[Product, dict]] = []
    for product in candidates:
        score = score_product(product, r)
        if score:
            scored.append((product, score))

    technical_match_count = len(scored)

    # Evidence can only reorder products with the same technical match score.
    # Keep every product tied at the Top-10 technical cutoff, but avoid loading
    # evidence for products that mathematically cannot reach the response.
    evidence_pool = _technical_evidence_pool(scored, limit=10)

    results = [
        {
            "product": serialize_product(product),
            **score,
        }
        for product, score in evidence_pool
    ]

    annotate_results_with_evidence(db, r, results)
    results.sort(key=evidence_sort_key, reverse=True)

    for row in results:
        row.pop("_evidence_completeness", None)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    logger.info(
        "Match completed in %.1f ms: sql_candidates=%d technical_matches=%d "
        "evidence_candidates=%d returned=%d",
        elapsed_ms,
        len(candidates),
        technical_match_count,
        len(evidence_pool),
        min(10, len(results)),
    )

    return {
        "count": technical_match_count,
        "matches": results[:10],
    }
