from __future__ import annotations

from collections import Counter
import json
import math
import re
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models import Product
from app.schemas import MatchRequest
from app.services.matching_engine import run_fast_technical_match


def _haystack(product: Product) -> str:
    return " ".join(
        [
            product.part_number or "",
            product.manufacturer or "",
            product.category or "",
            product.description or "",
            product.tags_json or "",
        ]
    ).lower()


def _raw(product: Product) -> dict:
    try:
        return json.loads(product.features.raw_features_json or "{}") if product.features else {}
    except Exception:
        return {}


def _cap(product: Product, key: str):
    return _raw(product).get(key)


def _generic_interface(product: Product):
    text = _haystack(product)
    values = []
    for value, pattern in [
        ("i2c", r"\bi2c\b|\bi²c\b"),
        ("spi", r"\bspi\b"),
        ("uart", r"\buart\b"),
        ("analog", r"\banalog(?:ue)?\b"),
        ("digital", r"\bdigital\s+(?:output|interface)\b"),
    ]:
        if re.search(pattern, text, re.I):
            values.append(value)
    if len(values) == 1:
        return values[0]
    return None


def _bluetooth_version(product: Product):
    text = _haystack(product)
    for pattern in [
        r"bluetooth(?:\s+le)?\s*([4-6](?:\.\d+)?)",
        r"\bble\s*([4-6](?:\.\d+)?)",
    ]:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return None


def _gnss_dual_band(product: Product):
    raw = _raw(product)
    if isinstance(raw.get("gnss_dual_band"), bool):
        return "dual" if raw["gnss_dual_band"] else "l1"

    text = _haystack(product)
    if re.search(r"\bl1\s*\+\s*l5\b|dual[- ]band\s+gnss|dual[- ]frequency\s+gnss", text, re.I):
        return "dual"
    if re.search(r"\bgnss\s*\(\s*l1\s*\)|\bsingle[- ]band\s+gnss\b", text, re.I):
        return "l1"
    return None


def _low_power(product: Product):
    raw = _raw(product)
    if raw.get("low_power_positive") is True:
        return "yes"
    if raw.get("low_power_negative") is True:
        return "no"
    text = _haystack(product)
    if re.search(r"\bultra[- ]?low[- ]?power\b|\blow[- ]?power\b|\blpwa\b", text, re.I):
        return "yes"
    return None


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def _format_capacitance_uf(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if number < 0.001:
        return f"{number * 1_000_000:g} pF"
    if number < 1:
        return f"{number * 1000:g} nF"
    return f"{number:g} µF"


def _fixed_options(key: str) -> list[dict]:
    options = {
        "cellularClass": [
            ("LTE-M / NB-IoT", "LPWA"),
            ("LTE Cat 1bis", "Cat 1bis"),
            ("LTE Cat 4", "Cat 4"),
            ("5G RedCap", "5G RedCap"),
        ],
        "region": [
            ("Global", "Global"),
            ("Americas", "Americas"),
            ("Europe / EMEA / APAC", "EMEA/APAC"),
        ],
        "architecture": [
            ("Open CPU", "open"),
            ("u-connectXpress / AT commands", "uconnect"),
            ("Host-based", "host"),
        ],
        "antenna": [
            ("Integrated / PCB antenna", "internal"),
            ("External antenna / antenna pin", "external"),
        ],
        "wifiGeneration": [
            ("Wi-Fi 4", "4"),
            ("Wi-Fi 5", "5"),
            ("Wi-Fi 6", "6"),
            ("Wi-Fi 6E", "6E"),
        ],
        "bluetoothRequirement": [
            ("Version open / not sure", "Bluetooth required, version open"),
            ("Bluetooth LE 5.0 or newer", "Bluetooth 5.0+"),
            ("Bluetooth LE 5.1 or newer", "Bluetooth 5.1+"),
            ("Bluetooth LE 5.2 or newer", "Bluetooth 5.2+"),
            ("Bluetooth LE 5.3 or newer", "Bluetooth 5.3+"),
            ("Bluetooth LE 5.4 or newer", "Bluetooth 5.4+"),
            ("Bluetooth LE 6.0 or newer", "Bluetooth 6.0+"),
        ],
        "gnssPrecision": [
            ("Standard GNSS / meter-level", "standard"),
            ("High precision / centimeter-level (RTK)", "cm"),
            ("No fixed accuracy / not sure", "No preference"),
        ],
        "gnssDualBand": [
            ("L1 is sufficient", "L1 sufficient"),
            ("Dual-band L1 + L5 required", "L1 + L5 required"),
            ("No preference / not sure", "No preference"),
        ],
        "genericInterface": [
            ("I²C", "i2c"),
            ("SPI", "spi"),
            ("Analog output", "analog"),
            ("Digital output", "digital"),
            ("UART", "uart"),
            ("No preference / not sure", "No preference"),
        ],
        "capacitorTechnology": [
            ("Ceramic / MLCC", "Ceramic"),
            ("Tantalum", "Tantalum"),
            ("Film", "Film"),
            ("Aluminum electrolytic", "Aluminum electrolytic"),
            ("Polymer", "Polymer"),
            ("Supercapacitor", "Supercapacitor"),
            ("No preference", "No preference"),
        ],
        "capacitorMounting": [
            ("SMD / SMT", "SMD"),
            ("Through-hole", "Through-hole"),
            ("No preference", "No preference"),
        ],
        "capacitorTolerance": [
            ("±5%", "±5%"),
            ("±10%", "±10%"),
            ("±20%", "±20%"),
            ("No preference", "No preference"),
        ],
        "lowPower": [
            ("Yes", True),
            ("No", False),
        ],
    }
    return [
        {"label": label, "value": value}
        for label, value in options.get(key, [])
    ]


QUESTION_TEXT = {
    "cellularClass": "Which cellular technology best fits the project?",
    "region": "Where will the product be deployed?",
    "architecture": "How should the wireless solution be controlled?",
    "antenna": "Which module antenna approach do you prefer?",
    "wifiGeneration": "Which Wi-Fi generations are acceptable? You can select more than one.",
    "bluetoothRequirement": "What minimum Bluetooth LE version does your application require?",
    "gnssPrecision": "What positioning performance does your application need?",
    "gnssDualBand": "Which GNSS frequency-band capability does your application need?",
    "genericInterface": "Do you have a preferred electrical interface or sensor output?",
    "capacitorCapacitance": "What capacitance do you need?",
    "capacitorVoltage": "What minimum voltage rating should the capacitor support?",
    "capacitorTechnology": "Do you have a preferred capacitor technology?",
    "capacitorMounting": "What mounting style do you need?",
    "capacitorTolerance": "Do you have a capacitance tolerance requirement?",
    "lowPower": "Is long battery life / low power consumption a major requirement?",
}


def _question_specs(request: MatchRequest) -> list[dict]:
    tech = set(request.technologies or [])
    specs: list[dict] = []

    def add(
        key: str,
        answered: bool,
        getter: Callable[[Product], Any],
        *,
        required: bool = True,
        priority: int = 50,
        multi_select: bool = False,
    ):
        if not answered:
            specs.append({
                "key": key,
                "getter": getter,
                "required": required,
                "priority": priority,
                "multi_select": multi_select,
            })

    if request.product_domain == "connectivity" or tech.intersection({"wifi", "bluetooth", "cellular", "gnss"}):
        if "cellular" in tech:
            add(
                "cellularClass",
                bool(request.cellular_class),
                lambda p: p.features.cellular_class if p.features else None,
                priority=96,
            )
            add(
                "region",
                bool(request.region),
                lambda p: p.features.region if p.features else None,
                priority=92,
            )

        if tech.intersection({"wifi", "bluetooth"}):
            add(
                "architecture",
                bool(request.architecture),
                lambda p: p.features.architecture if p.features else None,
                priority=94,
            )

        if "wifi" in tech:
            add(
                "wifiGeneration",
                bool(request.wifi_generation),
                lambda p: p.features.wifi_generation if p.features else None,
                priority=88,
                multi_select=True,
            )

        if "bluetooth" in tech:
            add(
                "bluetoothRequirement",
                request.bluetooth_required is True or bool(request.bluetooth_version_min),
                _bluetooth_version,
                priority=86,
            )
            add(
                "antenna",
                bool(request.antenna),
                lambda p: p.features.antenna if p.features else None,
                priority=80,
            )

        if "gnss" in tech:
            add(
                "gnssPrecision",
                bool(request.gnss_precision),
                lambda p: p.features.gnss_precision if p.features else None,
                priority=94,
            )
            add(
                "gnssDualBand",
                request.gnss_dual_band is not None,
                _gnss_dual_band,
                priority=90,
            )

        if request.application == "asset tracking":
            add(
                "lowPower",
                request.low_power is not None,
                _low_power,
                required=False,
                priority=62,
            )

    if request.product_domain == "positioning" and "gnss" not in tech:
        add(
            "gnssPrecision",
            bool(request.gnss_precision),
            lambda p: p.features.gnss_precision if p.features else None,
            priority=96,
        )
        add(
            "gnssDualBand",
            request.gnss_dual_band is not None,
            _gnss_dual_band,
            priority=92,
        )

    if request.product_domain == "sensors":
        add(
            "genericInterface",
            bool(request.generic_interface),
            _generic_interface,
            priority=90,
        )

    if request.catalog_category == "Capacitors":
        add(
            "capacitorCapacitance",
            request.capacitance_uf is not None,
            lambda p: _cap(p, "capacitance_uf"),
            priority=100,
        )
        add(
            "capacitorVoltage",
            request.capacitor_voltage_v is not None,
            lambda p: _cap(p, "capacitor_voltage_v"),
            priority=98,
        )
        add(
            "capacitorTechnology",
            bool(request.capacitor_technology),
            lambda p: _cap(p, "capacitor_technology"),
            priority=88,
        )
        add(
            "capacitorMounting",
            bool(request.capacitor_mounting),
            lambda p: _cap(p, "capacitor_mounting"),
            priority=80,
        )
        add(
            "capacitorTolerance",
            request.capacitor_tolerance_pct is not None,
            lambda p: _cap(p, "capacitor_tolerance_pct"),
            priority=74,
        )

    return specs


def _distribution(products: list[Product], getter: Callable[[Product], Any]) -> tuple[Counter, int]:
    values: Counter = Counter()
    known = 0

    for product in products:
        value = getter(product)
        if value is None or value == "":
            continue

        if isinstance(value, float):
            value = round(value, 8)

        values[str(value)] += 1
        known += 1

    return values, known


def _information_gain(distribution: Counter, known: int, total: int) -> tuple[float, float]:
    if total <= 0 or known <= 0:
        return 0.0, 0.0

    coverage = known / total
    if len(distribution) <= 1:
        return 0.0, coverage

    entropy = 0.0
    for count in distribution.values():
        probability = count / known
        entropy -= probability * math.log2(probability)

    # Coverage discount avoids over-valuing a beautiful split that is known
    # for only a tiny fraction of products. Cap at 3 bits so very high-cardinality
    # numeric fields do not completely dominate all engineering priorities.
    return min(entropy, 3.0) * coverage, coverage


def _dynamic_options(key: str, distribution: Counter) -> list[dict]:
    if key == "capacitorCapacitance":
        values = []
        for raw in distribution:
            try:
                values.append(float(raw))
            except ValueError:
                pass
        values = sorted(values)
        # Six representative values across the observed range.
        if len(values) > 6:
            indexes = sorted({round(i * (len(values) - 1) / 5) for i in range(6)})
            values = [values[i] for i in indexes]
        return [
            {"label": _format_capacitance_uf(value), "value": _format_capacitance_uf(value)}
            for value in values
        ]

    if key == "capacitorVoltage":
        values = []
        for raw in distribution:
            try:
                values.append(float(raw))
            except ValueError:
                pass
        values = sorted(values)
        if len(values) > 6:
            indexes = sorted({round(i * (len(values) - 1) / 5) for i in range(6)})
            values = [values[i] for i in indexes]
        return [
            {"label": f"{_format_number(value)} V", "value": f"{_format_number(value)} V"}
            for value in values
        ]

    return _fixed_options(key)


def choose_adaptive_question(db: Session, request: MatchRequest) -> dict:
    """
    Select the next engineering question using current candidate diversity.

    The engine does not invent requirements. It only changes *question order*
    according to which unanswered field can best discriminate the current
    candidate set. Core engineering fields remain required even when catalog
    data coverage is weak.
    """
    run = run_fast_technical_match(db, request)
    products = [product for product, _ in run.scored]
    specs = _question_specs(request)

    if not products or not specs:
        return {
            "candidate_count": len(products),
            "evaluated_fields": len(specs),
            "question": None,
        }

    ranked = []
    for spec in specs:
        distribution, known = _distribution(products, spec["getter"])
        gain, coverage = _information_gain(distribution, known, len(products))
        ranked.append({
            **spec,
            "distribution": distribution,
            "known": known,
            "information_gain": gain,
            "coverage": coverage,
        })

    required = [item for item in ranked if item["required"]]
    pool = required if required else [
        item for item in ranked if item["information_gain"] >= 0.10
    ]

    if not pool:
        return {
            "candidate_count": len(products),
            "evaluated_fields": len(specs),
            "question": None,
        }

    # Information gain drives the order. Engineering priority is only a
    # deterministic tie-breaker / weak-data fallback.
    best = max(
        pool,
        key=lambda item: (
            item["information_gain"],
            item["coverage"],
            item["priority"],
        ),
    )

    options = _dynamic_options(best["key"], best["distribution"])
    if not options:
        options = _fixed_options(best["key"])

    # If catalog-derived dynamic options are unavailable, the customer can
    # always type a value in the free-text box.
    question = {
        "key": best["key"],
        "text": QUESTION_TEXT[best["key"]],
        "options": options,
        "multi_select": best["multi_select"],
        "required": best["required"],
        "information_gain": round(best["information_gain"], 3),
        "known_coverage": round(best["coverage"], 3),
        "candidate_count": len(products),
        "distinct_known_values": len(best["distribution"]),
    }

    return {
        "candidate_count": len(products),
        "evaluated_fields": len(specs),
        "question": question,
    }
