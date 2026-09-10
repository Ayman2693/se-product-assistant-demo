from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Product
from app.schemas import (
    InterpretRequest,
    InterpretResponse,
    MatchRequest,
    NaturalRecommendRequest,
    NaturalRecommendResponse,
)
from app.routers.products import serialize_product
from app.services.matcher import score_product
from app.services.evidence_matcher import (
    annotate_results_with_evidence,
    evidence_sort_key,
)
from app.services.requirement_parser import (
    interpret_text,
    merge_requirements,
    missing_requirements,
    next_question,
)

router = APIRouter(prefix="/api/requirements", tags=["requirements"])

def _state_dict(state):
    if state is None:
        return {}
    return state.model_dump()

def _match(db: Session, req_dict: dict):
    request = MatchRequest(
        application=req_dict.get("application"),
        technologies=req_dict.get("technologies") or [],
        cellular_class=req_dict.get("cellular_class"),
        region=req_dict.get("region"),
        architecture=req_dict.get("architecture"),
        antenna=req_dict.get("antenna"),
        wifi_generation=req_dict.get("wifi_generation"),
        gnss_precision=req_dict.get("gnss_precision"),
        low_power=req_dict.get("low_power"),
        host_interface=req_dict.get("host_interface"),
        antenna_connector=req_dict.get("antenna_connector"),
        antenna_count=req_dict.get("antenna_count"),
        bluetooth_required=req_dict.get("bluetooth_required"),
        bluetooth_version_min=req_dict.get("bluetooth_version_min"),
        max_footprint_mm2=req_dict.get("max_footprint_mm2"),
        form_factor=req_dict.get("form_factor"),
        gnss_dual_band=req_dict.get("gnss_dual_band"),
        mandatory=[],
    )

    results = []
    for product in db.query(Product).all():
        score = score_product(product, request)
        if score:
            results.append({"product": serialize_product(product), **score})

    annotate_results_with_evidence(db, request, results)
    results.sort(key=evidence_sort_key, reverse=True)

    for row in results:
        row.pop("_evidence_completeness", None)

    return {"count": len(results), "matches": results[:10]}

@router.post("/interpret", response_model=InterpretResponse)
def interpret(request: InterpretRequest):
    parsed = interpret_text(request.text)
    merged = merge_requirements(_state_dict(request.current), parsed["requirements"])
    missing = missing_requirements(merged)

    return {
        "requirements": merged,
        "evidence": parsed["evidence"],
        "confidence": parsed["confidence"],
        "missing": missing,
        "next_question": next_question(merged),
    }

@router.post("/recommend", response_model=NaturalRecommendResponse)
def recommend(request: NaturalRecommendRequest, db: Session = Depends(get_db)):
    parsed = interpret_text(request.text)
    merged = merge_requirements(_state_dict(request.current), parsed["requirements"])
    missing = missing_requirements(merged)

    # We can still give a provisional result when the user supplied
    # at least technology + application, but "ready_to_match" means
    # all core technical qualification fields are known.
    ready = len(missing) == 0
    match = None

    if merged.get("technologies"):
        match = _match(db, merged)

    return {
        "requirements": merged,
        "evidence": parsed["evidence"],
        "confidence": parsed["confidence"],
        "missing": missing,
        "next_question": next_question(merged),
        "ready_to_match": ready,
        "match": match,
    }
