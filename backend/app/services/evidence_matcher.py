from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.models import ProductEvidence
from app.schemas import MatchRequest


MULTI_VALUE_FIELDS = {"technology", "interface", "antenna_connector"}
EXCLUSIVE_FIELDS = {
    "category",
    "cellular_class",
    "region",
    "architecture",
    "antenna",
    "wifi_generation",
    "gnss_precision",
    "bluetooth_version",
    "form_factor",
    "gnss_dual_band",
    "low_power",
    "footprint_mm2",
    "antenna_count",
    "capacitance_uf",
    "capacitor_voltage_v",
    "capacitor_tolerance_pct",
    "capacitor_technology",
    "capacitor_mounting",
    "capacitor_case_size",
    "capacitor_esr_ohm",
    "capacitor_ripple_current_a",
    "capacitor_lifetime_h",
    "capacitor_theoretical_energy_j",
    "temperature_min",
    "temperature_max",
}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _request_criteria(r: MatchRequest) -> list[dict]:
    criteria: list[dict] = []

    if r.catalog_category:
        criteria.append({
            "key": "catalog_category",
            "label": "Product type",
            "field": "category",
            "expected": r.catalog_category,
        })

    if r.generic_interface:
        criteria.append({
            "key": "generic_interface",
            "label": "Interface",
            "field": "interface",
            "expected": r.generic_interface,
        })

    for tech in r.technologies or []:
        criteria.append({
            "key": f"technology:{tech}",
            "label": f"{tech.upper()} capability",
            "field": "technology",
            "expected": tech,
        })

    if r.cellular_class:
        criteria.append({
            "key": "cellular_class",
            "label": "Cellular class",
            "field": "cellular_class",
            "expected": r.cellular_class,
        })

    if r.region:
        criteria.append({
            "key": "region",
            "label": "Deployment region",
            "field": "region",
            "expected": r.region,
        })

    if r.architecture:
        criteria.append({
            "key": "architecture",
            "label": "Architecture",
            "field": "architecture",
            "expected": r.architecture,
        })

    if r.antenna:
        criteria.append({
            "key": "antenna",
            "label": "Antenna",
            "field": "antenna",
            "expected": r.antenna,
        })

    if r.wifi_generation:
        criteria.append({
            "key": "wifi_generation",
            "label": "Wi-Fi generation",
            "field": "wifi_generation",
            "expected": r.wifi_generation,
        })

    if r.gnss_precision:
        criteria.append({
            "key": "gnss_precision",
            "label": "GNSS precision",
            "field": "gnss_precision",
            "expected": r.gnss_precision,
        })

    if r.host_interface:
        criteria.append({
            "key": "host_interface",
            "label": "Host interface",
            "field": "interface",
            "expected": r.host_interface,
        })

    if r.antenna_connector:
        criteria.append({
            "key": "antenna_connector",
            "label": "Antenna connector",
            "field": "antenna_connector",
            "expected": r.antenna_connector,
        })

    if r.antenna_count:
        criteria.append({
            "key": "antenna_count",
            "label": "Antenna connections",
            "field": "antenna_count",
            "expected": r.antenna_count,
        })

    # Avoid counting Bluetooth twice when it is already a requested technology.
    if r.bluetooth_required and "bluetooth" not in set(r.technologies or []):
        criteria.append({
            "key": "bluetooth_required",
            "label": "Bluetooth capability",
            "field": "technology",
            "expected": "bluetooth",
        })

    if r.bluetooth_version_min:
        criteria.append({
            "key": "bluetooth_version_min",
            "label": "Minimum Bluetooth version",
            "field": "bluetooth_version",
            "expected": r.bluetooth_version_min,
        })

    if r.max_footprint_mm2:
        criteria.append({
            "key": "max_footprint_mm2",
            "label": "Maximum footprint",
            "field": "footprint_mm2",
            "expected": r.max_footprint_mm2,
        })

    if r.form_factor:
        criteria.append({
            "key": "form_factor",
            "label": "Form factor",
            "field": "form_factor",
            "expected": r.form_factor,
        })

    if r.gnss_dual_band:
        criteria.append({
            "key": "gnss_dual_band",
            "label": "Dual-band GNSS",
            "field": "gnss_dual_band",
            "expected": True,
        })

    if r.low_power:
        criteria.append({
            "key": "low_power",
            "label": "Low-power characteristics",
            "field": "low_power",
            "expected": True,
        })

    if r.catalog_category == "Capacitors":
        if r.capacitance_uf is not None:
            criteria.append({
                "key": "capacitance_uf",
                "label": "Capacitance",
                "field": "capacitance_uf",
                "expected": r.capacitance_uf,
            })
        if r.capacitor_voltage_v is not None:
            criteria.append({
                "key": "capacitor_voltage_v",
                "label": "Voltage rating",
                "field": "capacitor_voltage_v",
                "expected": r.capacitor_voltage_v,
            })
        if r.capacitor_tolerance_pct is not None:
            criteria.append({
                "key": "capacitor_tolerance_pct",
                "label": "Tolerance",
                "field": "capacitor_tolerance_pct",
                "expected": r.capacitor_tolerance_pct,
            })
        if r.capacitor_technology and r.capacitor_technology.lower() not in {"any", "no preference"}:
            criteria.append({
                "key": "capacitor_technology",
                "label": "Capacitor technology",
                "field": "capacitor_technology",
                "expected": r.capacitor_technology,
            })
        if r.capacitor_mounting and r.capacitor_mounting.lower() not in {"any", "no preference"}:
            criteria.append({
                "key": "capacitor_mounting",
                "label": "Mounting",
                "field": "capacitor_mounting",
                "expected": r.capacitor_mounting,
            })
        if r.capacitor_case_size:
            criteria.append({
                "key": "capacitor_case_size",
                "label": "Case size",
                "field": "capacitor_case_size",
                "expected": r.capacitor_case_size,
            })
        if r.capacitor_esr_max_ohm is not None:
            criteria.append({
                "key": "capacitor_esr_max_ohm",
                "label": "Maximum ESR",
                "field": "capacitor_esr_ohm",
                "expected": r.capacitor_esr_max_ohm,
            })
        if r.capacitor_ripple_current_min_a is not None:
            criteria.append({
                "key": "capacitor_ripple_current_min_a",
                "label": "Minimum ripple current",
                "field": "capacitor_ripple_current_a",
                "expected": r.capacitor_ripple_current_min_a,
            })
        if r.capacitor_lifetime_min_h is not None:
            criteria.append({
                "key": "capacitor_lifetime_min_h",
                "label": "Minimum lifetime",
                "field": "capacitor_lifetime_h",
                "expected": r.capacitor_lifetime_min_h,
            })
        if r.capacitor_temperature_min_c is not None:
            criteria.append({
                "key": "capacitor_temperature_min_c",
                "label": "Minimum operating temperature",
                "field": "temperature_min",
                "expected": r.capacitor_temperature_min_c,
            })
        if r.capacitor_temperature_max_c is not None:
            criteria.append({
                "key": "capacitor_temperature_max_c",
                "label": "Maximum operating temperature",
                "field": "temperature_max",
                "expected": r.capacitor_temperature_max_c,
            })
        if r.capacitor_energy_min_j is not None:
            criteria.append({
                "key": "capacitor_energy_min_j",
                "label": "Minimum theoretical stored energy",
                "field": "capacitor_theoretical_energy_j",
                "expected": r.capacitor_energy_min_j,
            })

    return criteria


def _supports(field: str, actual: Any, expected: Any) -> bool:
    a = _norm(actual)

    if not a:
        return False

    if field == "wifi_generation":
        expected_values = expected if isinstance(expected, (list, tuple, set)) else [expected]
        return a in {_norm(value) for value in expected_values}

    e = _norm(expected)

    if field == "technology":
        return a == e

    if field == "cellular_class":
        if e == "lpwa":
            return a in {"lpwa", "lte-m", "ltem", "nb-iot", "nbiot"}
        return a.replace(" ", "") == e.replace(" ", "")

    if field == "region":
        if e == "global":
            return a == "global"
        if "america" in e:
            return a in {"global", "americas", "america"}
        if "emea" in e or "apac" in e or "europe" in e:
            return a in {"global", "emea/apac", "emea", "apac", "europe"}
        return a == e

    if field == "antenna":
        if e == "internal":
            return a in {"internal", "both"}
        if e == "external":
            return a in {"external", "both"}
        return a == e

    if field == "gnss_precision":
        if e == "cm":
            return a == "cm"
        if e == "standard":
            return a in {"standard", "cm"}
        return a == e

    if field == "interface":
        if e == "sdio_pcie":
            return a in {"sdio", "pcie"}
        return a == e

    if field == "bluetooth_version":
        try:
            return float(a) >= float(e)
        except (TypeError, ValueError):
            return False

    if field == "footprint_mm2":
        try:
            return float(a) <= float(e)
        except (TypeError, ValueError):
            return False

    if field in {"gnss_dual_band", "low_power"}:
        return a in {"true", "1", "yes"} if bool(expected) else a in {"false", "0", "no"}

    if field == "antenna_count":
        try:
            return int(float(a)) == int(expected)
        except (TypeError, ValueError):
            return False

    if field == "capacitance_uf":
        try:
            av, ev = float(a), float(e)
            scale = max(abs(av), abs(ev), 1e-12)
            return abs(av - ev) <= scale * 0.002
        except (TypeError, ValueError):
            return False

    if field in {"capacitor_voltage_v", "capacitor_ripple_current_a", "capacitor_lifetime_h", "capacitor_theoretical_energy_j", "temperature_max"}:
        try:
            return float(a) >= float(e)
        except (TypeError, ValueError):
            return False

    if field in {"capacitor_tolerance_pct", "capacitor_esr_ohm", "temperature_min"}:
        try:
            return float(a) <= float(e)
        except (TypeError, ValueError):
            return False

    if field == "capacitor_technology":
        if e == "polymer":
            return "polymer" in a
        if e == "tantalum":
            return "tantal" in a
        if e == "ceramic":
            return "ceramic" in a or "mlcc" in a
        if e == "film":
            return "film" in a
        if e == "supercapacitor":
            return "supercapacitor" in a
        return a == e

    return a == e


def _source_payload(row: ProductEvidence | None) -> dict:
    if row is None:
        return {
            "evidence_value": None,
            "source_type": None,
            "source_title": None,
            "source_url": None,
            "page_number": None,
            "confidence": None,
        }

    page_number = None
    if row.locations:
        page_number = sorted(
            row.locations,
            key=lambda loc: (loc.page_number, loc.id),
        )[0].page_number

    return {
        "evidence_value": row.value_text or row.normalized_value,
        "source_type": row.source_type or None,
        "source_title": row.source_title or None,
        "source_url": row.source_url or None,
        "page_number": page_number,
        "confidence": float(row.confidence) if row.confidence is not None else None,
    }


def _best(rows: list[ProductEvidence]) -> ProductEvidence | None:
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda row: (
            1 if row.document_id is not None else 0,
            float(row.confidence or 0.0),
            row.id,
        ),
        reverse=True,
    )[0]


def _criterion_result(
    criterion: dict,
    evidence_rows: list[ProductEvidence],
) -> dict:
    field = criterion["field"]
    expected = criterion["expected"]

    field_rows = [
        row for row in evidence_rows
        if row.field_name == field
    ]

    verified_support = [
        row for row in field_rows
        if row.verification_status == "verified"
        and _supports(field, row.normalized_value, expected)
    ]

    if verified_support:
        row = _best(verified_support)
        return {
            "key": criterion["key"],
            "label": criterion["label"],
            "requested_value": str(expected),
            "status": "verified",
            **_source_payload(row),
        }

    # An explicit verified value on a single-valued field contradicts the
    # requested requirement when none of the verified rows support it.
    verified_values = [
        row for row in field_rows
        if row.verification_status == "verified"
    ]
    if verified_values and field in EXCLUSIVE_FIELDS:
        row = _best(verified_values)
        return {
            "key": criterion["key"],
            "label": criterion["label"],
            "requested_value": str(expected),
            "status": "conflicting",
            **_source_payload(row),
        }

    inferred_support = [
        row for row in field_rows
        if row.verification_status == "inferred"
        and _supports(field, row.normalized_value, expected)
    ]
    if inferred_support:
        row = _best(inferred_support)
        return {
            "key": criterion["key"],
            "label": criterion["label"],
            "requested_value": str(expected),
            "status": "inferred",
            **_source_payload(row),
        }

    inferred_values = [
        row for row in field_rows
        if row.verification_status == "inferred"
    ]
    if inferred_values and field in EXCLUSIVE_FIELDS:
        row = _best(inferred_values)
        return {
            "key": criterion["key"],
            "label": criterion["label"],
            "requested_value": str(expected),
            "status": "conflicting",
            **_source_payload(row),
        }

    return {
        "key": criterion["key"],
        "label": criterion["label"],
        "requested_value": str(expected),
        "status": "not_verified",
        **_source_payload(None),
    }


def _summary(items: list[dict]) -> dict:
    total = len(items)
    counts = {
        "verified": 0,
        "inferred": 0,
        "not_verified": 0,
        "conflicting": 0,
    }

    for item in items:
        status = item["status"]
        if status in counts:
            counts[status] += 1

    if total:
        # Evidence score is documentation confidence, not technical match.
        # Verified = 100%, inferred = 55%, unknown = 0%, conflict = -50%.
        raw = (
            counts["verified"] * 100
            + counts["inferred"] * 55
            - counts["conflicting"] * 50
        ) / total
        evidence_score = max(0, min(100, round(raw)))
    else:
        evidence_score = 0

    return {
        "total": total,
        **counts,
        "evidence_score": evidence_score,
    }


def annotate_results_with_evidence(
    db: Session,
    request: MatchRequest,
    results: list[dict],
) -> list[dict]:
    if not results:
        return results

    product_ids = [row["product"]["id"] for row in results]

    rows = (
        db.query(ProductEvidence)
        .options(selectinload(ProductEvidence.locations))
        .filter(ProductEvidence.product_id.in_(product_ids))
        .all()
    )

    by_product: dict[int, list[ProductEvidence]] = defaultdict(list)
    for row in rows:
        by_product[row.product_id].append(row)

    criteria = _request_criteria(request)

    for result in results:
        evidence_items = [
            _criterion_result(criterion, by_product.get(result["product"]["id"], []))
            for criterion in criteria
        ]
        summary = _summary(evidence_items)

        result["criterion_evidence"] = evidence_items
        result["evidence_summary"] = summary
        result["evidence_score"] = summary["evidence_score"]

    return results


def evidence_sort_key(result: dict) -> tuple:
    summary = result.get("evidence_summary") or {}
    return (
        result.get("match_percent", 0),
        result.get("evidence_score", 0),
        summary.get("verified", 0),
        -summary.get("conflicting", 0),
        result.get("_evidence_completeness", 0),
        1
        if result.get("product", {}).get("features")
        and result["product"]["features"].get("imported_live")
        else 0,
    )
