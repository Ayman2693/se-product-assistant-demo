from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import time

from sqlalchemy import or_
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.matcher import score_product

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


@dataclass
class TechnicalMatchRun:
    candidates: list[Product]
    scored: list[tuple[Product, dict]]
    candidate_load_ms: float = 0.0
    scoring_ms: float = 0.0
    mode: str = "fast"


def _text_has_any(terms: list[str]):
    """Broad SQL predicate used only as a conservative recall-first pre-filter."""
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


def _word_variants(word: str) -> list[str]:
    """
    Conservative singular/plural variants for catalog category pre-filtering.

    This is deliberately simple. It is a *superset* filter only; the existing
    deterministic matcher remains authoritative.
    """
    values = {word}
    if word.endswith("ies") and len(word) > 4:
        values.add(word[:-3] + "y")
    elif word.endswith("s") and len(word) > 4:
        values.add(word[:-1])
    else:
        values.add(word + "s")
    return sorted(values)


def category_prefilter_terms(category: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (category or "").lower())
    specific = [
        word
        for word in words
        if len(word) >= 3 and word not in _GENERIC_CATEGORY_WORDS
    ]
    selected = specific[:4] if specific else words[:2]

    terms: list[str] = []
    for word in selected:
        terms.extend(_word_variants(word))

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(terms))


def technology_prefilter(technology: str):
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
            ProductFeature.technologies_json.ilike("%ble%"),
            # "ble" is intentionally broad here. False positives cost a little
            # performance; false negatives would damage recommendation recall.
            _text_has_any(["bluetooth", "ble", "bt/ble"]),
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


def candidate_query(db: Session, request: MatchRequest):
    """
    SQL pre-filter + eager load of the one-to-one Product.features relation.

    The query must remain recall-first. It may return extra candidates, because
    score_product() is still the source of truth for technical eligibility.
    """
    query = (
        db.query(Product)
        .outerjoin(ProductFeature, ProductFeature.product_id == Product.id)
        .options(contains_eager(Product.features))
    )
    applied_filters = False

    if request.catalog_category:
        terms = category_prefilter_terms(request.catalog_category)
        clauses = [
            Product.category.ilike(f"%{term}%")
            for term in terms
        ]
        if clauses:
            query = query.filter(or_(*clauses))
            applied_filters = True

    requested_technologies = list(request.technologies or [])
    if request.bluetooth_required and "bluetooth" not in requested_technologies:
        requested_technologies.append("bluetooth")

    for technology in requested_technologies:
        clause = technology_prefilter(technology)
        if clause is not None:
            # Existing matcher treats every requested technology as mandatory,
            # so AND across technologies is correct here.
            query = query.filter(clause)
            applied_filters = True

    return query, applied_filters


def load_fast_candidates(db: Session, request: MatchRequest) -> list[Product]:
    query, applied_filters = candidate_query(db, request)
    candidates = query.all()

    # Safety fallback. If a pre-filter unexpectedly produces no rows, prefer
    # correctness over speed and scan the complete catalog.
    if not candidates and applied_filters:
        logger.warning(
            "Fast candidate pre-filter returned zero rows; falling back to exhaustive catalog load."
        )
        return load_exhaustive_candidates(db)

    return candidates


def load_exhaustive_candidates(db: Session) -> list[Product]:
    return db.query(Product).options(joinedload(Product.features)).all()


def score_candidates(products: list[Product], request: MatchRequest) -> list[tuple[Product, dict]]:
    scored: list[tuple[Product, dict]] = []
    for product in products:
        score = score_product(product, request)
        if score:
            scored.append((product, score))
    return scored


def run_fast_technical_match(db: Session, request: MatchRequest) -> TechnicalMatchRun:
    started = time.perf_counter()
    candidates = load_fast_candidates(db, request)
    after_load = time.perf_counter()
    scored = score_candidates(candidates, request)
    finished = time.perf_counter()

    return TechnicalMatchRun(
        candidates=candidates,
        scored=scored,
        candidate_load_ms=(after_load - started) * 1000.0,
        scoring_ms=(finished - after_load) * 1000.0,
        mode="fast",
    )


def run_exhaustive_technical_match(db: Session, request: MatchRequest) -> TechnicalMatchRun:
    started = time.perf_counter()
    candidates = load_exhaustive_candidates(db)
    after_load = time.perf_counter()
    scored = score_candidates(candidates, request)
    finished = time.perf_counter()

    return TechnicalMatchRun(
        candidates=candidates,
        scored=scored,
        candidate_load_ms=(after_load - started) * 1000.0,
        scoring_ms=(finished - after_load) * 1000.0,
        mode="exhaustive",
    )


def technical_evidence_pool(
    scored: list[tuple[Product, dict]],
    limit: int = 10,
) -> list[tuple[Product, dict]]:
    """
    Return every product that can still enter top-N after evidence tie-breaking.

    Evidence is forbidden from promoting a lower technical match percentage
    above a higher one, so only candidates at/above the Nth technical score
    need evidence. Every candidate tied at the cutoff remains in the pool.
    """
    if len(scored) <= limit:
        return list(scored)

    ordered = sorted(
        scored,
        key=lambda item: item[1].get("match_percent", 0),
        reverse=True,
    )
    cutoff = ordered[limit - 1][1].get("match_percent", 0)
    return [
        item
        for item in ordered
        if item[1].get("match_percent", 0) >= cutoff
    ]


def compare_fast_vs_exhaustive(
    db: Session,
    request: MatchRequest,
    limit: int = 10,
) -> dict:
    """
    Compare the optimized path with a complete-catalog technical scan.

    The primary quality invariant is recall: every product that is a valid
    technical match in the exhaustive path must also survive the fast
    pre-filter. We also compare the full top-cutoff pool used before evidence.
    """
    fast = run_fast_technical_match(db, request)
    exhaustive = run_exhaustive_technical_match(db, request)

    fast_ids = {product.id for product, _ in fast.scored}
    exhaustive_ids = {product.id for product, _ in exhaustive.scored}

    fast_top_ids = {
        product.id for product, _ in technical_evidence_pool(fast.scored, limit)
    }
    exhaustive_top_ids = {
        product.id for product, _ in technical_evidence_pool(exhaustive.scored, limit)
    }

    missing_ids = sorted(exhaustive_ids - fast_ids)
    missing_top_ids = sorted(exhaustive_top_ids - fast_top_ids)

    return {
        "ok": not missing_ids and not missing_top_ids,
        "fast_candidates": len(fast.candidates),
        "exhaustive_candidates": len(exhaustive.candidates),
        "fast_matches": len(fast.scored),
        "exhaustive_matches": len(exhaustive.scored),
        "missing_match_ids": missing_ids,
        "missing_top_cutoff_ids": missing_top_ids,
        "fast_top_cutoff_ids": sorted(fast_top_ids),
        "exhaustive_top_cutoff_ids": sorted(exhaustive_top_ids),
        "fast_candidate_load_ms": round(fast.candidate_load_ms, 2),
        "fast_scoring_ms": round(fast.scoring_ms, 2),
        "exhaustive_candidate_load_ms": round(exhaustive.candidate_load_ms, 2),
        "exhaustive_scoring_ms": round(exhaustive.scoring_ms, 2),
    }
