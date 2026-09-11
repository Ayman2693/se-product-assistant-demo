import json
import re
from app.models import Product, ProductFeature
from app.schemas import MatchRequest
from app.services.engineering_profiles import field_spec
from app.services.engineering_features import (
    compare_engineering_value,
    engineering_reason,
    raw_engineering_from_feature_json,
)

def _haystack(p: Product) -> str:
    return " ".join([
        p.part_number or "",
        p.manufacturer or "",
        p.category or "",
        p.description or "",
        p.tags_json or "",
    ]).lower()

def _feature_tech(feature: ProductFeature | None) -> list[str]:
    if not feature:
        return []
    try:
        return json.loads(feature.technologies_json or "[]")
    except Exception:
        return []

def _raw_features(feature: ProductFeature | None) -> dict:
    if not feature:
        return {}
    try:
        return json.loads(feature.raw_features_json or "{}")
    except Exception:
        return {}


def _capacitor_features(p: Product) -> dict:
    raw = _raw_features(p.features)
    keys = {
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
    }
    return {key: raw.get(key) for key in keys}


def _float_equal(actual, expected, rel_tol: float = 0.002) -> bool:
    try:
        a = float(actual)
        e = float(expected)
    except (TypeError, ValueError):
        return False
    scale = max(abs(a), abs(e), 1e-12)
    return abs(a - e) <= scale * rel_tol


def _capacitor_technology_matches(actual: str, expected: str) -> bool:
    a = (actual or "").lower()
    e = (expected or "").lower()
    if not a or not e:
        return False
    if e in {"any", "no preference"}:
        return True
    if e == "polymer":
        return "polymer" in a
    if e == "tantalum":
        return "tantal" in a
    if e == "ceramic":
        return "ceramic" in a or "mlcc" in a
    if e == "film":
        return "film" in a
    if e == "aluminum electrolytic":
        return "aluminum electrolytic" in a or "aluminium electrolytic" in a
    if e == "supercapacitor":
        return "supercapacitor" in a
    return a == e


def _low_power_state(p: Product) -> int:
    """
     1 = positive evidence
     0 = not verified
    -1 = explicit negative evidence
    """
    raw = _raw_features(p.features)
    if raw.get("low_power_negative") is True:
        return -1
    if raw.get("low_power_positive") is True:
        return 1

    h = _haystack(p)

    # Safety fallback for old rows before backfill.
    if re.search(
        r"\bw/?o\s+low[- ]?power\b|\bwithout\s+low[- ]?power\b|\bno\s+low[- ]?power\b",
        h,
        re.I,
    ):
        return -1

    if re.search(
        r"\blow[- ]?power\b|\bultra[- ]?low[- ]?power\b|\bbattery[- ]?powered\b|\blpwa\b|\blte-?m\b|\bnb-?iot\b",
        h,
        re.I,
    ):
        return 1

    return 0

def _evidence_completeness(p: Product) -> int:
    """Tie-breaker: prefer products with more verified structured catalog evidence."""
    f = p.features
    if not f:
        return 0

    points = 0
    for value in [
        f.cellular_class,
        f.region,
        f.gnss_precision,
        f.wifi_generation,
        f.architecture,
        f.antenna,
        f.form_factor,
    ]:
        if value not in (None, ""):
            points += 1

    if f.has_gnss is not None:
        points += 1
    if f.has_bluetooth is not None:
        points += 1
    if f.temperature_min is not None and f.temperature_max is not None:
        points += 1
    if f.imported_live:
        points += 1

    return points

def _contains(h: str, *terms: str) -> bool:
    return any(t.lower() in h for t in terms)

def _generic_interfaces(h: str) -> set[str]:
    values: set[str] = set()
    patterns = [
        ("i2c", r"\bi2c\b|\bi²c\b"),
        ("spi", r"\bspi\b"),
        ("uart", r"\buart\b"),
        ("usb", r"\busb\b"),
        ("sdio", r"\bsdio\b"),
        ("pcie", r"\bpcie\b|\bpci express\b"),
        ("analog", r"\banalog(?:ue)?\s+(?:output|interface)|\b4\s*-\s*20\s*ma\b|\b0\s*-\s*10\s*v\b"),
        ("digital", r"\bdigital\s+(?:output|interface)\b"),
    ]
    for value, pattern in patterns:
        if re.search(pattern, h, re.I):
            values.add(value)
    return values


def _catalog_category_matches(actual: str | None, wanted: str) -> bool:
    if not actual:
        return False
    a = re.sub(r"\s+", " ", actual.strip().lower())
    w = re.sub(r"\s+", " ", wanted.strip().lower())
    return a == w or w in a or a in w


def _host_interfaces(h: str) -> set[str]:
    values: set[str] = set()
    if re.search(r"\bsdio\b", h, re.I):
        values.add("sdio")
    # Avoid treating "Mini PCIe form factor" as definitive host-interface evidence.
    pcie_text = re.sub(r"\bmini\s*pci[eE]?\b", " ", h, flags=re.I)
    if re.search(r"\bpcie\b|\bpci express\b", pcie_text, re.I):
        values.add("pcie")
    return values

def _antenna_connectors(h: str) -> set[str]:
    values: set[str] = set()
    if re.search(r"\bu\.?fl\b|\bufl\b", h, re.I):
        values.add("ufl")
    if re.search(r"antenna[- ]?pin|ant\.?\s*pins?|solder\s*pads?", h, re.I):
        values.add("antenna_pin")
    return values

def _antenna_count(h: str) -> int | None:
    patterns = [
        r"\b([1-4])\s*x\s*u\.?fl\b",
        r"\b([1-4])\s*(?:antenna\s*pins?|ant\.?\s*pins?)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, h, re.I)
        if m:
            return int(m.group(1))
    return None


def _antenna_applications(p: Product) -> set[str]:
    raw = _raw_features(p.features)
    values = {str(v).lower() for v in (raw.get("antenna_applications") or []) if v}
    if values:
        return values

    h = _haystack(p)
    if re.search(r"\bgnss\b|\bgps\b|\bgalileo\b|\bglonass\b|\bbeidou\b|\bl1\b|\bl2\b|\bl5\b", h, re.I):
        values.add("gnss")
    if re.search(r"wi-?fi|\bwlan\b|bluetooth|\bble\b|\b2[.,]4\s*ghz\b", h, re.I):
        values.add("wifi_bt")
    if re.search(r"\bcellular\b|\blte\b|\b5g\b|\b4g\b|\bgsm\b|\bumts\b|\blte-?m\b|\bnb-?iot\b", h, re.I):
        values.add("cellular")
    if re.search(r"\blora\b|\bsigfox\b|\bism\b|\bsub[- ]?ghz\b|\b433\s*mhz\b|\b868\s*mhz\b|\b915\s*mhz\b", h, re.I):
        values.add("ism")
    return values


def _antenna_band_capabilities(p: Product) -> set[str]:
    raw = _raw_features(p.features)
    values = {str(v).lower() for v in (raw.get("antenna_bands") or []) if v}
    if values:
        return values

    h = _haystack(p)
    l1 = bool(re.search(r"\bl1\b|1559\s*[-–]\s*1609|155[0-9]\s*[-–]\s*16[0-1][0-9]\s*mhz", h, re.I))
    multiband = bool(re.search(
        r"dual[- ]band\s+gnss|multi[- ]band\s+gnss|"
        r"\bl1\s*[/+]\s*l2\b|\bl1\s*[/+]\s*l5\b|"
        r"\bl1\s*[/+]\s*l2\s*[/+]\s*l5\b|\bl2\b|\bl5\b|"
        r"11(?:6[0-9]|7[0-9]|8[0-9]|9[0-9])\s*[-–]\s*12[0-9]{2}",
        h,
        re.I,
    ))
    if l1:
        values.add("gnss_l1")
    if multiband:
        values.add("gnss_multiband")
        if l1:
            values.add("gnss_l1")

    wifi_6e = bool(re.search(r"wi-?fi\s*6e|\b6e\b|\b6\s*ghz\b|59[2-9][0-9]\s*mhz|6[0-9]{3}\s*mhz", h, re.I))
    wifi_5 = bool(re.search(r"\b5\s*ghz\b|49[0-9]{2}\s*mhz|5[0-8][0-9]{2}\s*mhz", h, re.I))
    wifi_24 = bool(re.search(r"\b2[.,]4\s*ghz\b|24[0-9]{2}\s*mhz|bluetooth|\bble\b", h, re.I))
    if wifi_24:
        values.add("wifi_24")
    if wifi_24 and wifi_5:
        values.add("wifi_245")
    if wifi_6e:
        values.add("wifi_6e")
    return values


def _antenna_active_value(p: Product) -> bool | None:
    raw = _raw_features(p.features)
    if isinstance(raw.get("antenna_active"), bool):
        return raw["antenna_active"]

    h = _haystack(p)
    if re.search(r"\bpassive\b[^.;]{0,24}\b(?:gnss\s+)?(?:patch\s+)?antenna\b|\bpassive\s+gnss\b", h, re.I):
        return False
    if re.search(r"\bactive\b[^.;]{0,24}\b(?:gnss\s+)?(?:patch\s+)?antenna\b|\bactive\s+gnss\b", h, re.I):
        return True
    return None


def _antenna_application_state(p: Product, wanted: str) -> int:
    actual = _antenna_applications(p)
    wanted = (wanted or "").lower()
    if not actual:
        return 0
    if wanted == "multi":
        return 1 if len(actual) >= 2 else -1
    return 1 if wanted in actual else -1


def _antenna_band_state(p: Product, wanted: str) -> int:
    actual = _antenna_band_capabilities(p)
    if not actual:
        return 0
    return 1 if (wanted or "").lower() in actual else -1

def _bluetooth_version(h: str) -> float | None:
    patterns = [
        r"bluetooth\s*([4-6](?:\.\d+)?)",
        r"\bble\s*([4-6](?:\.\d+)?)",
        r"\bbt\s*/\s*ble\s*([4-6](?:\.\d+)?)",
        r"\bbt\s*([4-6](?:\.\d+)?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, h, re.I)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None

def _footprint_mm2(h: str) -> float | None:
    # Product descriptions commonly contain dimensions such as 10.4x14.3x1.9mm.
    m = re.search(
        r"(?<!\d)(\d{1,3}(?:[.,]\d+)?)\s*[x×]\s*(\d{1,3}(?:[.,]\d+)?)(?:\s*[x×]\s*\d{1,3}(?:[.,]\d+)?)?\s*mm\b",
        h,
        re.I,
    )
    if not m:
        return None
    try:
        a = float(m.group(1).replace(",", "."))
        b = float(m.group(2).replace(",", "."))
        if 0 < a <= 200 and 0 < b <= 200:
            return round(a * b, 2)
    except ValueError:
        pass
    return None

def _gnss_dual_band(h: str) -> bool | None:
    if re.search(r"\bl1\s*\+\s*l5\b|dual[- ]band\s+gnss|dual[- ]frequency\s+gnss", h, re.I):
        return True
    if re.search(r"\bgnss\s*\(\s*l1\s*\)|\bgnss\b[^.;]{0,30}\bl1\b", h, re.I):
        return False
    return None


def _wifi_generation_from_text(h: str):
    if re.search(r"wi-?fi\s*6e|6\s*ghz", h, re.I):
        return "6E"
    if re.search(r"wi-?fi\s*6\b|802\.11ax\b", h, re.I):
        return "6"
    if re.search(r"wi-?fi\s*5\b|802\.11ac\b|\bwi-?fi\s*ac\b", h, re.I):
        return "5"
    if re.search(r"wi-?fi\s*4\b|802\.11n\b", h, re.I):
        return "4"
    return None


_CONNECTIVITY_TECHNOLOGIES = {"wifi", "bluetooth", "cellular", "gnss"}


def _product_connectivity_technologies(p: Product) -> set[str]:
    """
    Return connectivity capabilities visible in structured catalog data or
    explicit product text. Used only as a ranking tie-break, never to turn an
    otherwise valid product into a hard mismatch.
    """
    techs = {
        str(value).lower()
        for value in _feature_tech(p.features)
        if str(value).lower() in _CONNECTIVITY_TECHNOLOGIES
    }

    h = _haystack(p)

    if re.search(r"wi-?fi|wlan|802\.11", h, re.I):
        techs.add("wifi")
    if re.search(r"bluetooth|\bble\b|\bbt\s*/\s*ble\b|\bbt\s*\d", h, re.I):
        techs.add("bluetooth")
    if re.search(r"\bgnss\b|\bgps\b|\brtk\b|galileo|glonass|beidou", h, re.I):
        techs.add("gnss")
    if re.search(r"lte-?m|nb-?iot|cat\.?\s*(?:1bis|1|4)|5g\s*redcap|cellular modem", h, re.I):
        techs.add("cellular")

    return techs


def _solution_scope_fit(p: Product, r: MatchRequest) -> tuple[int, list[str]]:
    """
    Prefer the simplest connectivity solution when technical fit is tied.

    Example:
      request = Bluetooth only
      Bluetooth-only module   -> scope 100
      Wi-Fi + Bluetooth       -> scope 85

    Extra capabilities never eliminate a product and never override a higher
    technical match percentage. They only order technically equal products.
    """
    requested = {
        str(value).lower()
        for value in (r.technologies or [])
        if str(value).lower() in _CONNECTIVITY_TECHNOLOGIES
    }

    # Direct API clients can express Bluetooth via bluetooth_required without
    # repeating it in technologies.
    if r.bluetooth_required:
        requested.add("bluetooth")

    if not requested:
        return 100, []

    actual = _product_connectivity_technologies(p)

    # If the matcher could verify the requested technology only through a
    # path not represented here, do not penalize uncertainty.
    if not requested.issubset(actual):
        return 100, []

    extra = sorted(actual - requested)
    score = max(0, 100 - 15 * len(extra))
    return score, extra


def _product_role(p: Product) -> str:
    category = (p.category or "").lower()
    pn = (p.part_number or "").lower()
    desc = (p.description or "").lower()

    if "evaluation" in category or pn.startswith(("evk-", "eval-", "dk-")) or "evaluation kit" in desc:
        return "evaluation"

    if "antenna" in category:
        return "antenna"

    if any(x in category for x in ("accessor", "adapter", "cable")):
        return "accessory"

    if re.search(r"\bm\.?2\s+card\b|mini\s*pci[eE]?\s+card", desc, re.I):
        return "card"

    return "primary"


def _role_allowed_for_request(p: Product, r: MatchRequest) -> bool:
    """
    For connectivity module searches, do not mix EVKs, standalone antennas,
    or accessories into the primary recommendation set.
    """
    role = _product_role(p)
    connectivity = {"wifi", "bluetooth", "cellular", "gnss"}
    requested = set(r.technologies or [])

    if requested & connectivity:
        if role in {"evaluation", "antenna", "accessory"}:
            return False

    return True

def score_product(p: Product, r: MatchRequest):
    if not _role_allowed_for_request(p, r):
        return None

    h = _haystack(p)
    f = p.features
    techs = set(_feature_tech(f))

    earned = 0.0
    possible = 0.0
    preference_penalty = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    def criterion(weight: int, state: int, reason: str, mandatory: bool = False):
        """
        state:
          1 = verified match
          0 = unknown / not verified
         -1 = verified mismatch

        Explicit negative evidence on a preferred criterion must rank below
        merely unknown evidence.
        """
        nonlocal earned, possible, preference_penalty
        if state == 1:
            possible += weight
            earned += weight
            reasons.append(reason)
        elif state == 0:
            possible += weight
            warnings.append(f"Not verified: {reason}")
        else:
            possible += weight
            if mandatory:
                raise ValueError("mandatory_mismatch")
            preference_penalty += weight * 0.65
            warnings.append(f"Does not match: {reason}")

    try:
        if r.catalog_category:
            state = 1 if _catalog_category_matches(p.category, r.catalog_category) else -1
            criterion(40, state, f"Product type: {r.catalog_category}", True)

        # Standalone antenna qualification: category alone is not sufficient
        # to call GNSS, Wi-Fi and cellular antennas equally suitable.
        if r.product_domain == "antenna" or (r.catalog_category and "Antenna" in r.catalog_category):
            if r.antenna_application:
                app_labels = {
                    "gnss": "GNSS",
                    "wifi_bt": "Wi-Fi / Bluetooth",
                    "cellular": "Cellular / LTE / 5G",
                    "ism": "ISM / LPWAN",
                    "multi": "Multi-radio / combination",
                }
                criterion(
                    34,
                    _antenna_application_state(p, r.antenna_application),
                    f"Antenna application: {app_labels.get(r.antenna_application, r.antenna_application)}",
                    True,
                )

            if r.antenna_band:
                band_labels = {
                    "gnss_l1": "GNSS L1",
                    "gnss_multiband": "GNSS multi-band (L1 + L2/L5)",
                    "wifi_24": "2.4 GHz",
                    "wifi_245": "2.4 + 5 GHz",
                    "wifi_6e": "6 GHz / Wi-Fi 6E capable",
                }
                criterion(
                    26,
                    _antenna_band_state(p, r.antenna_band),
                    f"Antenna band: {band_labels.get(r.antenna_band, r.antenna_band)}",
                    True,
                )

            if r.antenna_active is not None:
                actual_active = _antenna_active_value(p)
                state = 0 if actual_active is None else (1 if actual_active == r.antenna_active else -1)
                criterion(
                    16,
                    state,
                    f"Antenna type: {'Active' if r.antenna_active else 'Passive'}",
                    True,
                )

        # Capacitor-domain engineering qualification. Known hard mismatches
        # eliminate a part; missing catalog data remains "Not verified" so we
        # never invent an absence.
        if r.catalog_category == "Capacitors":
            cap = _capacitor_features(p)

            if r.capacitance_uf is not None:
                actual = cap.get("capacitance_uf")
                state = 0 if actual is None else (1 if _float_equal(actual, r.capacitance_uf) else -1)
                criterion(34, state, f"Capacitance: {r.capacitance_uf:g} µF", True)

            if r.capacitor_voltage_v is not None:
                actual = cap.get("capacitor_voltage_v")
                if actual is None:
                    state = 0
                else:
                    try:
                        state = 1 if float(actual) >= float(r.capacitor_voltage_v) else -1
                    except (TypeError, ValueError):
                        state = 0
                criterion(26, state, f"Voltage rating ≥ {r.capacitor_voltage_v:g} V", True)

            if r.capacitor_technology and r.capacitor_technology.lower() not in {"any", "no preference"}:
                actual = cap.get("capacitor_technology")
                state = 0 if not actual else (1 if _capacitor_technology_matches(str(actual), r.capacitor_technology) else -1)
                criterion(18, state, f"Technology: {r.capacitor_technology}", True)

            if r.capacitor_mounting and r.capacitor_mounting.lower() not in {"any", "no preference"}:
                actual = cap.get("capacitor_mounting")
                state = 0 if not actual else (1 if str(actual).lower() == r.capacitor_mounting.lower() else -1)
                criterion(14, state, f"Mounting: {r.capacitor_mounting}", True)

            if r.capacitor_tolerance_pct is not None:
                actual = cap.get("capacitor_tolerance_pct")
                if actual is None:
                    state = 0
                else:
                    try:
                        # A tighter tolerance is acceptable: ±5% satisfies ±10%.
                        state = 1 if float(actual) <= float(r.capacitor_tolerance_pct) else -1
                    except (TypeError, ValueError):
                        state = 0
                criterion(11, state, f"Tolerance ≤ ±{r.capacitor_tolerance_pct:g}%", False)

            if r.capacitor_case_size:
                actual = cap.get("capacitor_case_size")
                state = 0 if not actual else (1 if str(actual).lower() == r.capacitor_case_size.lower() else -1)
                criterion(10, state, f"Case size: {r.capacitor_case_size}", False)

            if r.capacitor_esr_max_ohm is not None:
                actual = cap.get("capacitor_esr_ohm")
                if actual is None:
                    state = 0
                else:
                    try:
                        state = 1 if float(actual) <= float(r.capacitor_esr_max_ohm) else -1
                    except (TypeError, ValueError):
                        state = 0
                criterion(12, state, f"ESR ≤ {r.capacitor_esr_max_ohm:g} Ω", False)

            if r.capacitor_ripple_current_min_a is not None:
                actual = cap.get("capacitor_ripple_current_a")
                if actual is None:
                    state = 0
                else:
                    try:
                        state = 1 if float(actual) >= float(r.capacitor_ripple_current_min_a) else -1
                    except (TypeError, ValueError):
                        state = 0
                criterion(12, state, f"Ripple current ≥ {r.capacitor_ripple_current_min_a:g} A", False)

            if r.capacitor_lifetime_min_h is not None:
                actual = cap.get("capacitor_lifetime_h")
                if actual is None:
                    state = 0
                else:
                    try:
                        state = 1 if int(actual) >= int(r.capacitor_lifetime_min_h) else -1
                    except (TypeError, ValueError):
                        state = 0
                criterion(10, state, f"Lifetime ≥ {r.capacitor_lifetime_min_h} h", False)

            if r.capacitor_temperature_min_c is not None:
                actual = f.temperature_min if f else None
                if actual is None:
                    state = 0
                else:
                    state = 1 if float(actual) <= float(r.capacitor_temperature_min_c) else -1
                criterion(8, state, f"Minimum operating temperature ≤ {r.capacitor_temperature_min_c:g} °C", False)

            if r.capacitor_temperature_max_c is not None:
                actual = f.temperature_max if f else None
                if actual is None:
                    state = 0
                else:
                    state = 1 if float(actual) >= float(r.capacitor_temperature_max_c) else -1
                criterion(8, state, f"Maximum operating temperature ≥ {r.capacitor_temperature_max_c:g} °C", False)

            if r.capacitor_energy_min_j is not None:
                actual = cap.get("capacitor_theoretical_energy_j")
                if actual is None:
                    state = 0
                else:
                    try:
                        state = 1 if float(actual) >= float(r.capacitor_energy_min_j) else -1
                    except (TypeError, ValueError):
                        state = 0
                criterion(
                    10,
                    state,
                    f"Theoretical stored energy ≥ {r.capacitor_energy_min_j:g} J",
                    False,
                )

        # Universal schema-driven engineering constraints. These requirements
        # are category-specific but evaluated by one deterministic engine.
        engineering_actual = raw_engineering_from_feature_json(
            f.raw_features_json if f else None
        )
        for key, expected in (r.engineering_requirements or {}).items():
            spec = field_spec(key)
            if spec is None:
                continue
            actual = engineering_actual.get(key)
            state = compare_engineering_value(spec, actual, expected)
            criterion(spec.weight, state, engineering_reason(spec, expected), True)

        if r.generic_interface:
            actual_interfaces = _generic_interfaces(h)
            wanted_interface = r.generic_interface.lower()
            if not actual_interfaces:
                state = 0
            elif wanted_interface in actual_interfaces:
                state = 1
            else:
                # Other explicit interfaces are not enough to prove absence of
                # the requested interface, so keep this conservative.
                state = 0
            criterion(14, state, f"Interface: {r.generic_interface.upper()}", False)

        for tech in r.technologies:
            structured = tech in techs
            if tech == "cellular":
                fallback = bool(re.search(r"lte-?m|nb-?iot|cat\.?\s*(?:1bis|1|4)|5g\s*redcap|cellular modem", h, re.I))
            elif tech == "bluetooth":
                fallback = bool(re.search(r"bluetooth|\bble\b|\bbt\s*/\s*ble\b|\bbt\s*\d", h, re.I))
            elif tech == "wifi":
                fallback = bool(re.search(r"wi-?fi|wlan|802\.11", h, re.I))
            elif tech == "gnss":
                fallback = bool(re.search(r"\bgnss\b|\bgps\b|\brtk\b|galileo|glonass|beidou", h, re.I))
            else:
                fallback = tech.lower() in h
            criterion(30, 1 if structured or fallback else -1, f"{tech.upper()} capability", True)

        if r.cellular_class:
            if f and f.cellular_class:
                state = 1 if f.cellular_class.lower() == r.cellular_class.lower() else -1
            else:
                state = 1 if r.cellular_class.lower() in h else 0
            criterion(22, state, f"{r.cellular_class} matches", True)

        if r.region:
            state = 0
            if f and f.region:
                wanted = r.region.lower()
                actual = f.region.lower()
                if wanted == "global":
                    state = 1 if actual == "global" else -1
                elif "america" in wanted:
                    state = 1 if actual in {"global", "americas"} else -1
                elif "emea" in wanted or "apac" in wanted:
                    state = 1 if actual in {"global", "emea/apac"} else -1
            criterion(14, state, f"Deployment region: {r.region}", True)

        if r.architecture:
            if f and f.architecture:
                state = 1 if f.architecture == r.architecture else -1
            else:
                if r.architecture == "open":
                    state = 1 if _contains(h, "open cpu", "open-cpu") else 0
                elif r.architecture == "uconnect":
                    state = 1 if _contains(h, "u-connect", "uconnect", "at command") else 0
                else:
                    state = 1 if _contains(h, "host-based", "host based") else 0
            criterion(16, state, f"Architecture: {r.architecture}", True)

        if r.antenna:
            if f and f.antenna:
                state = 1 if f.antenna in {r.antenna, "both"} else -1
            else:
                state = 0
            criterion(13, state, f"Antenna: {r.antenna}", True)

        if r.wifi_generation:
            acceptable_wifi = {str(g).lower() for g in r.wifi_generation}
            actual_wifi = f.wifi_generation if (f and f.wifi_generation) else _wifi_generation_from_text(h)
            if actual_wifi:
                state = 1 if actual_wifi.lower() in acceptable_wifi else -1
            else:
                state = 0
            wifi_label = " / ".join(f"Wi-Fi {g}" for g in r.wifi_generation)
            criterion(18, state, f"Acceptable generation: {wifi_label}", True)

        if r.gnss_precision:
            if f and f.has_gnss is False:
                state = -1
            elif f and f.gnss_precision:
                if r.gnss_precision == "cm":
                    state = 1 if f.gnss_precision == "cm" else -1
                else:
                    state = 1 if f.gnss_precision in {"standard", "cm"} else 0
            else:
                if r.gnss_precision == "cm":
                    state = 1 if re.search(r"\brtk\b|high precision|centimeter|centimetre", h, re.I) else 0
                else:
                    state = 1 if re.search(r"\bgnss\b|\bgps\b", h, re.I) else 0
            criterion(18, state, f"GNSS precision: {r.gnss_precision}", True)

        if r.host_interface:
            actual_ifaces = _host_interfaces(h)
            wanted = r.host_interface.lower()
            if not actual_ifaces:
                state = 0
            elif wanted == "sdio_pcie":
                # "SDIO or PCIe" means either supported interface is acceptable.
                state = 1 if actual_ifaces.intersection({"sdio", "pcie"}) else -1
            else:
                state = 1 if wanted in actual_ifaces else -1
            criterion(14, state, f"Host interface: {r.host_interface}", True)

        if r.antenna_connector:
            actual_connectors = _antenna_connectors(h)
            wanted = r.antenna_connector.lower()
            if not actual_connectors:
                state = 0
            else:
                state = 1 if wanted in actual_connectors else -1
            label = "U.FL" if wanted == "ufl" else "antenna pin"
            criterion(10, state, f"Antenna connector: {label}", True)

        if r.antenna_count:
            actual_count = _antenna_count(h)
            if actual_count is None:
                state = 0
            else:
                state = 1 if actual_count == r.antenna_count else -1
            criterion(8, state, f"Antenna connections: {r.antenna_count}", True)

        # Do not score Bluetooth capability twice when it is already present
        # in technologies. bluetooth_required exists for direct API callers
        # that may request Bluetooth without populating technologies.
        if r.bluetooth_required and "bluetooth" not in set(r.technologies or []):
            bt_capable = "bluetooth" in techs or bool(
                re.search(r"bluetooth|\bble\b|\bbt\s*/\s*ble\b|\bbt\s*\d", h, re.I)
            )
            criterion(14, 1 if bt_capable else -1, "Bluetooth capability", True)

        if r.bluetooth_version_min:
            actual_bt = _bluetooth_version(h)
            try:
                wanted_bt = float(r.bluetooth_version_min)
            except (TypeError, ValueError):
                wanted_bt = None
            if wanted_bt is not None:
                if actual_bt is None:
                    state = 0
                else:
                    state = 1 if actual_bt >= wanted_bt else -1
                criterion(10, state, f"Bluetooth >= {r.bluetooth_version_min}", True)

        if r.max_footprint_mm2:
            actual_area = _footprint_mm2(h)
            if actual_area is None:
                state = 0
            else:
                state = 1 if actual_area <= r.max_footprint_mm2 else -1
            criterion(10, state, f"Footprint <= {r.max_footprint_mm2:g} mm²", True)

        if r.form_factor:
            wanted_ff = r.form_factor.lower()
            if f and f.form_factor:
                state = 1 if f.form_factor.lower() == wanted_ff else -1
            else:
                state = 1 if wanted_ff in h else 0
            criterion(12, state, f"Form factor: {r.form_factor}", True)

        if r.gnss_dual_band:
            actual_dual = _gnss_dual_band(h)
            if actual_dual is None:
                state = 0
            else:
                state = 1 if actual_dual else -1
            criterion(12, state, "Dual-band GNSS (L1+L5)", True)

        if r.low_power:
            lp_state = _low_power_state(p)
            if lp_state == 1:
                criterion(12, 1, "Low-power characteristics", False)
            elif lp_state == -1:
                criterion(12, -1, "Low-power characteristics", False)
            else:
                criterion(12, 0, "Low-power characteristics", False)

        if f and f.imported_live:
            criterion(5, 1, "Current SE catalog record", False)
        if p.availability and p.availability != "Check live SE page":
            criterion(5, 1, f"Availability: {p.availability}", False)

    except ValueError:
        return None

    if possible == 0:
        return None

    score = round((earned - preference_penalty) / possible * 100)

    # Avoid presenting poorly verified products as perfect recommendations.
    if warnings:
        score = min(score, 94)

    solution_scope_score, extra_technologies = _solution_scope_fit(p, r)

    return {
        "match_percent": max(0, min(100, score)),
        "reasons": (reasons + warnings)[:8],
        "solution_scope_score": solution_scope_score,
        "extra_technologies": extra_technologies,
        "_evidence_completeness": _evidence_completeness(p),
    }
