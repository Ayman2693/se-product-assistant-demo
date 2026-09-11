import asyncio
import json
from datetime import datetime, timezone
import logging
import random
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.catalog_sources import CATALOG_SOURCES
from app.db import SessionLocal, get_db
from app.models import Product, ProductFeature
from app.schemas import CatalogStatusResponse, MatchRequest, MatchResponse, ProductOut
from app.config import settings
from app.services.matching_engine import (
    load_fast_candidates as _load_match_candidates,
    run_fast_technical_match,
    technical_evidence_pool as _technical_evidence_pool,
)
from app.services.quality_guard import run_shadow_quality_guard
from app.services.family_graph import (
    annotate_results_with_families,
    rebuild_family_graph,
)
from app.services.catalog_importer import import_catalog
from app.services.evidence_service import seed_catalog_evidence
from app.services.evidence_matcher import (
    annotate_results_with_evidence,
    evidence_sort_key,
)


logger = logging.getLogger(__name__)

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

        _catalog_sync_state["status"] = "rebuilding_family_graph"
        family_graph = rebuild_family_graph(db)
        db.commit()

        _catalog_sync_state.update({
            "status": "completed",
            "finished_at": _utcnow_iso(),
            "products_seen": result.get("products_seen", 0),
            "sources_succeeded": result.get("sources_succeeded", 0),
            "sources_completed": result.get("sources_completed", 0),
            "sources_requested": result.get("sources_requested", 0),
            "failed": result.get("failed", []),
            "evidence": evidence,
            "family_graph": family_graph,
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
def match_products(
    r: MatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    started = time.perf_counter()

    technical = run_fast_technical_match(db, r)
    technical_match_count = len(technical.scored)
    evidence_pool = _technical_evidence_pool(technical.scored, limit=10)

    results = [
        {
            "product": serialize_product(product),
            **score,
        }
        for product, score in evidence_pool
    ]

    evidence_started = time.perf_counter()
    annotate_results_with_evidence(db, r, results)
    results.sort(key=evidence_sort_key, reverse=True)
    annotate_results_with_families(db, results)
    evidence_ms = (time.perf_counter() - evidence_started) * 1000.0

    for row in results:
        row.pop("_evidence_completeness", None)
        row.pop("_recommendation_safety_rank", None)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    logger.info(
        "Match completed %.1f ms | candidate_load=%.1f ms scoring=%.1f ms "
        "evidence=%.1f ms | sql_candidates=%d technical_matches=%d "
        "evidence_candidates=%d returned=%d",
        elapsed_ms,
        technical.candidate_load_ms,
        technical.scoring_ms,
        evidence_ms,
        len(technical.candidates),
        technical_match_count,
        len(evidence_pool),
        min(10, len(results)),
    )

    sample_rate = max(0.0, min(1.0, settings.match_quality_guard_sample_rate))
    if sample_rate and random.random() < sample_rate:
        # Runs after the response has been sent and uses its own DB session.
        background_tasks.add_task(run_shadow_quality_guard, r.model_dump())

    return {
        "count": technical_match_count,
        "matches": results[:10],
    }
