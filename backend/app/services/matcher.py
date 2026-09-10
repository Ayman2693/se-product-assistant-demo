import json
import re
from app.models import Product, ProductFeature
from app.schemas import MatchRequest

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
            actual_wifi = f.wifi_generation if (f and f.wifi_generation) else _wifi_generation_from_text(h)
            if actual_wifi:
                state = 1 if actual_wifi.lower() == r.wifi_generation.lower() else -1
            else:
                state = 0
            criterion(18, state, f"Wi-Fi {r.wifi_generation}", True)

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

        if r.bluetooth_required:
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

    return {
        "match_percent": max(0, min(100, score)),
        "reasons": (reasons + warnings)[:8],
        "_evidence_completeness": _evidence_completeness(p),
    }
