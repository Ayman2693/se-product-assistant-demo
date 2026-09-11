from __future__ import annotations

import logging

from app.db import SessionLocal
from app.schemas import MatchRequest
from app.services.matching_engine import compare_fast_vs_exhaustive

logger = logging.getLogger(__name__)


def run_shadow_quality_guard(request_dict: dict) -> None:
    """
    Background-only exhaustive comparison.

    This never changes the customer response. It exists to prove that the
    optimized candidate pre-filter is not losing valid technical matches.
    """
    db = SessionLocal()
    try:
        request = MatchRequest(**request_dict)
        result = compare_fast_vs_exhaustive(db, request)

        if result["ok"]:
            logger.info(
                "MATCH_QUALITY_GUARD PASS fast_candidates=%d exhaustive_candidates=%d "
                "fast_matches=%d exhaustive_matches=%d",
                result["fast_candidates"],
                result["exhaustive_candidates"],
                result["fast_matches"],
                result["exhaustive_matches"],
            )
        else:
            logger.error(
                "MATCH_QUALITY_GUARD FAIL missing_matches=%s missing_top_cutoff=%s "
                "fast_candidates=%d exhaustive_candidates=%d",
                result["missing_match_ids"],
                result["missing_top_cutoff_ids"],
                result["fast_candidates"],
                result["exhaustive_candidates"],
            )
    except Exception:
        logger.exception("MATCH_QUALITY_GUARD ERROR")
    finally:
        db.close()
