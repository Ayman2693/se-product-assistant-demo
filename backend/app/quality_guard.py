"""Run exhaustive-vs-fast quality checks against the current product database.

Usage from backend:
    python -m app.quality_guard
"""

from app.db import SessionLocal
from app.schemas import MatchRequest
from app.services.matching_engine import compare_fast_vs_exhaustive


SCENARIOS = [
    ("Wi-Fi 5/6", MatchRequest(technologies=["wifi"], wifi_generation=["5", "6"])),
    ("Bluetooth LE", MatchRequest(technologies=["bluetooth"], bluetooth_required=True)),
    ("GNSS", MatchRequest(technologies=["gnss"])),
    ("Capacitors", MatchRequest(catalog_category="Capacitors")),
    ("Pressure sensors", MatchRequest(product_domain="sensors", catalog_category="Pressure Sensors")),
    ("Single Board Computer", MatchRequest(product_domain="computing", catalog_category="Single Board Computer")),
]


def main() -> None:
    db = SessionLocal()
    failed = False
    try:
        for name, request in SCENARIOS:
            result = compare_fast_vs_exhaustive(db, request)
            status = "PASS" if result["ok"] else "FAIL"
            print(
                f"{status:4} | {name:24} | "
                f"fast candidates {result['fast_candidates']:4} / "
                f"catalog {result['exhaustive_candidates']:4} | "
                f"matches {result['fast_matches']:4}"
            )
            if not result["ok"]:
                failed = True
                print("      missing matches:", result["missing_match_ids"][:30])
                print("      missing top-cutoff:", result["missing_top_cutoff_ids"][:30])
    finally:
        db.close()

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
