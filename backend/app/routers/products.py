import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
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

router = APIRouter(prefix="/api", tags=["products"])

_catalog_sync_task: asyncio.Task | None = None
_catalog_sync_state = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "products_seen": 0,
    "sources_succeeded": 0,
    "sources_requested": 0,
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
        "sources_requested": 0,
        "failed": [],
        "error": None,
    })

    db = SessionLocal()
    try:
        result = await import_catalog(
            db,
            discover_descendants=True,
        )
        evidence = seed_catalog_evidence(db)

        _catalog_sync_state.update({
            "status": "completed",
            "finished_at": _utcnow_iso(),
            "products_seen": result.get("products_seen", 0),
            "sources_succeeded": result.get("sources_succeeded", 0),
            "sources_requested": result.get("sources_requested", 0),
            "failed": result.get("failed", []),
            "evidence": evidence,
        })
    except Exception as exc:
        _catalog_sync_state.update({
            "status": "failed",
            "finished_at": _utcnow_iso(),
            "error": str(exc),
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


def _json(value, fallback):
    try:
        return json.loads(value or "")
    except Exception:
        return fallback

def serialize_features(f: ProductFeature | None):
    if not f:
        return None
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
    results = []
    for p in db.query(Product).all():
        score = score_product(p, r)
        if not score:
            continue
        results.append({
            "product": serialize_product(p),
            **score,
        })

    # Phase 4.3:
    # Technical fit remains the primary ranking key.
    # Evidence quality is used only to order technically tied products.
    annotate_results_with_evidence(db, r, results)
    results.sort(key=evidence_sort_key, reverse=True)

    for row in results:
        row.pop("_evidence_completeness", None)

    return {"count": len(results), "matches": results[:10]}
