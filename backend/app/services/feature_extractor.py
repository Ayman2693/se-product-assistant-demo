import json
import re
from typing import Any

from app.services.engineering_features import extract_engineering_features

def _norm(value: str | None) -> str:
    return (value or "").lower().replace("–", "-").replace("—", "-")

def _first(patterns, text):
    for value, pattern in patterns:
        if re.search(pattern, text, flags=re.I):
            return value
    return None

def _temperature(text: str):
    """
    Parse only explicit temperature expressions.
    Important: avoid interpreting product numbers such as W377-10C as 377…10 °C.
    Supported examples:
      -40/+85°C
      -30 to +85°C
      -40 ... +85 °C
      -40…+85°C
    """
    patterns = [
        r"(?<![A-Za-z0-9])(-?\d{1,3})\s*/\s*\+?(-?\d{1,3})\s*°\s*C\b",
        r"(?<![A-Za-z0-9])(-?\d{1,3})\s*(?:to|\.\.\.|…)\s*\+?(-?\d{1,3})\s*°\s*C\b",
        r"(?<![A-Za-z0-9])(-?\d{1,3})\s*°\s*C\s*(?:to|\.\.\.|…|-)\s*\+?(-?\d{1,3})\s*°\s*C\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if not m:
            continue
        try:
            lo = float(m.group(1))
            hi = float(m.group(2))
        except ValueError:
            continue
        # Sanity range for electronic product operating/storage temperatures.
        if -100 <= lo <= 200 and -100 <= hi <= 200 and lo <= hi:
            return lo, hi
    return None, None


_CAP_UF_FACTORS = {
    "pf": 1e-6,
    "nf": 1e-3,
    "uf": 1.0,
    "µf": 1.0,
    "μf": 1.0,
    "mf": 1e3,
    "f": 1e6,
}


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def _capacitance_uf(text: str) -> float | None:
    m = re.search(
        r"(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)\s*(pF|nF|uF|µF|μF|mF|F)\b",
        text,
        re.I,
    )
    if not m:
        return None
    return _number(m.group(1)) * _CAP_UF_FACTORS[m.group(2).lower()]


def _capacitor_voltage_v(text: str) -> float | None:
    # Prefer explicitly labelled rated/working voltage.
    labelled = re.search(
        r"(?:rated|working|nominal)?\s*(?:voltage|spannung|nennspannung)"
        r"\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*v\b",
        text,
        re.I,
    )
    if labelled:
        return _number(labelled.group(1))

    # On capacitor catalog cards a standalone value such as "25 V" is
    # conventionally the voltage rating. Keep this fallback capacitor-only.
    m = re.search(r"(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)\s*v\b", text, re.I)
    return _number(m.group(1)) if m else None


def _capacitor_tolerance_pct(text: str) -> float | None:
    m = re.search(
        r"(?:±|\+/-|\+-)\s*(\d+(?:[.,]\d+)?)\s*%|"
        r"(?:tolerance|toleranz)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%",
        text,
        re.I,
    )
    if not m:
        return None
    value = m.group(1) or m.group(2)
    return _number(value)


def _capacitor_technology(text: str) -> str | None:
    t = _norm(text)
    if re.search(r"\bsuper\s*cap(?:acitor)?s?\b|\bsupercapacitor\b|\bultracap\b|\bedlc\b", t):
        return "Supercapacitor"
    if "tantal" in t and "polymer" in t:
        return "Tantalum polymer"
    if "alumin" in t and "polymer" in t:
        return "Aluminum polymer"
    if re.search(r"\btantal(?:um)?\b|\btantalelko\b", t):
        return "Tantalum"
    if re.search(r"\bceramic\b|\bmlcc\b|\bkeramik\b|\bx7r\b|\bx5r\b|\bc0g\b|\bnp0\b|\by5v\b", t):
        return "Ceramic"
    if re.search(r"\bfilm\b|\bfolienkondensator\b|\bpolypropylene\b|\bpolyester\b", t):
        return "Film"
    if re.search(r"\balumin(?:um|ium)\b.*\belectrolytic\b|\belko\b|\belektrolyt", t):
        return "Aluminum electrolytic"
    if re.search(r"\bpolymer\b", t):
        return "Polymer"
    return None


def _capacitor_mounting(text: str) -> str | None:
    t = _norm(text)
    if re.search(r"\bthrough[- ]?hole\b|\btht\b|\bradial\b|\baxial\b|\bleaded\b|\bdrahtanschluss\b", t):
        return "Through-hole"
    if re.search(r"\bsmd\b|\bsmt\b|\bchip\b|\bsurface[- ]?mount", t):
        return "SMD"
    return None


def _capacitor_case_size(text: str) -> str | None:
    # Common passive SMD imperial package codes. Requiring boundaries avoids
    # matching arbitrary digits embedded inside manufacturer part numbers.
    m = re.search(
        r"(?<![A-Za-z0-9])(?:case|package|bauform|size)?\s*"
        r"(0201|0402|0603|0805|1206|1210|1812|2220)(?![A-Za-z0-9])",
        text,
        re.I,
    )
    return m.group(1) if m else None


def _capacitor_esr_ohm(text: str) -> float | None:
    m = re.search(
        r"(?:\besr\b|equivalent\s+series\s+resistance)"
        r"[^0-9]{0,12}(\d+(?:[.,]\d+)?)\s*(mohm|mω|mΩ|ohm|ω|Ω)",
        text,
        re.I,
    )
    if not m:
        return None
    value = _number(m.group(1))
    unit = m.group(2).lower()
    return value / 1000.0 if unit.startswith("m") else value


def _capacitor_ripple_current_a(text: str) -> float | None:
    m = re.search(
        r"(?:ripple\s*current|ripple|rippelstrom|ripple-strom)"
        r"[^0-9]{0,16}(\d+(?:[.,]\d+)?)\s*(ma|a)\b",
        text,
        re.I,
    )
    if not m:
        return None
    value = _number(m.group(1))
    return value / 1000.0 if m.group(2).lower() == "ma" else value


def _capacitor_lifetime_h(text: str) -> int | None:
    m = re.search(
        r"(?:life(?:time)?|load\s+life|service\s+life|lebensdauer)"
        r"[^0-9]{0,16}(\d{2,7})\s*(?:h|hours?|stunden)\b",
        text,
        re.I,
    )
    return int(m.group(1)) if m else None


def _wifi_generation(text: str):
    t = _norm(text)
    if re.search(r"wi-?fi\s*6e|802\.11ax[^.;,]*6\s*ghz|\b6\s*ghz\b", t):
        return "6E"
    if re.search(r"wi-?fi\s*6\b|802\.11ax\b", t):
        return "6"
    if re.search(r"wi-?fi\s*5\b|802\.11ac\b|\bwi-?fi\s*ac\b", t):
        return "5"
    if re.search(r"wi-?fi\s*4\b|802\.11n\b|802\.11bgn\b|\bwi-?fi\s*[abg]*n\b", t):
        return "4"
    return None


def _antenna_catalog_profile(text: str, category: str) -> tuple[list[str], list[str], bool | None]:
    """Extract conservative standalone-antenna qualifiers from SE catalog text."""
    t = _norm(text)
    category_l = _norm(category)
    if "antenna" not in category_l and "antenna" not in t and "ant." not in t:
        return [], [], None

    apps: list[str] = []
    bands: list[str] = []

    if re.search(r"\bgnss\b|\bgps\b|\bgalileo\b|\bglonass\b|\bbeidou\b|\bl1\b|\bl2\b|\bl5\b", t, re.I):
        apps.append("gnss")
    if re.search(r"wi-?fi|\bwlan\b|bluetooth|\bble\b|\b2[.,]4\s*ghz\b", t, re.I):
        apps.append("wifi_bt")
    if re.search(r"\bcellular\b|\blte\b|\b5g\b|\b4g\b|\bgsm\b|\bumts\b|\blte-?m\b|\bnb-?iot\b", t, re.I):
        apps.append("cellular")
    if re.search(r"\blora\b|\bsigfox\b|\bism\b|\bsub[- ]?ghz\b|\b433\s*mhz\b|\b868\s*mhz\b|\b915\s*mhz\b", t, re.I):
        apps.append("ism")

    if "gnss" in apps:
        l1 = bool(re.search(r"\bl1\b|1559\s*[-–]\s*1609|155[0-9]\s*[-–]\s*16[0-1][0-9]\s*mhz", t, re.I))
        multiband = bool(re.search(
            r"dual[- ]band\s+gnss|multi[- ]band\s+gnss|"
            r"\bl1\s*[/+]\s*l2\b|\bl1\s*[/+]\s*l5\b|"
            r"\bl1\s*[/+]\s*l2\s*[/+]\s*l5\b|\bl2\b|\bl5\b|"
            r"11(?:6[0-9]|7[0-9]|8[0-9]|9[0-9])\s*[-–]\s*12[0-9]{2}",
            t,
            re.I,
        ))
        if l1:
            bands.append("gnss_l1")
        if multiband:
            bands.append("gnss_multiband")
            if l1:
                bands.append("gnss_l1")

    if "wifi_bt" in apps:
        wifi_6e = bool(re.search(r"wi-?fi\s*6e|\b6e\b|\b6\s*ghz\b|59[2-9][0-9]\s*mhz|6[0-9]{3}\s*mhz", t, re.I))
        wifi_5 = bool(re.search(r"\b5\s*ghz\b|49[0-9]{2}\s*mhz|5[0-8][0-9]{2}\s*mhz", t, re.I))
        wifi_24 = bool(re.search(r"\b2[.,]4\s*ghz\b|24[0-9]{2}\s*mhz|bluetooth|\bble\b", t, re.I))
        if wifi_24:
            bands.append("wifi_24")
        if wifi_24 and wifi_5:
            bands.append("wifi_245")
        if wifi_6e:
            bands.append("wifi_6e")

    active: bool | None = None
    if re.search(r"\bpassive\b[^.;]{0,24}\b(?:gnss\s+)?(?:patch\s+)?antenna\b|\bpassive\s+gnss\b", t, re.I):
        active = False
    elif re.search(r"\bactive\b[^.;]{0,24}\b(?:gnss\s+)?(?:patch\s+)?antenna\b|\bactive\s+gnss\b", t, re.I):
        active = True

    return sorted(set(apps)), sorted(set(bands)), active

def extract_features(part_number: str, manufacturer: str, category: str, description: str, tags=None) -> dict[str, Any]:
    tags = tags or []
    text = " ".join([part_number or "", manufacturer or "", category or "", description or "", *tags])
    t = _norm(text)

    # Phrases such as "no LTE filter" describe RF coexistence/filtering, not cellular capability.
    cellular_text = re.sub(r"\b(?:no\s+)?lte\s+filter\b", " ", t)
    cellular_text = re.sub(r"\blte\s+coexistence\b", " ", cellular_text)

    technologies = []

    category_l = _norm(category)
    cellular_category = any(k in category_l for k in ("lte", "cellular", "5g redcap", "nb-iot"))
    explicit_cellular = re.search(
        r"\b(?:lte-?m|nb-?iot|cat\.?\s*(?:1bis|1|4)\b|5g\s*redcap|cellular modem|cellular module|gsm|umts)\b",
        cellular_text,
        flags=re.I,
    )
    if cellular_category or explicit_cellular:
        technologies.append("cellular")

    # Recognize Bluetooth, BLE and compact forms such as BT5.3 or BT/BLE.
    if re.search(
        r"bluetooth|\bble\s*\d(?:\.\d+)?\b|\bble\b|\bbt\s*/\s*ble\b|\bbt\s*\d(?:\.\d+)?\b",
        t,
        flags=re.I,
    ):
        technologies.append("bluetooth")

    if re.search(r"wi-?fi|wlan|802\.11", t, flags=re.I):
        technologies.append("wifi")

    if re.search(r"\bgnss\b|\bgps\b|\brtk\b|galileo|glonass|beidou|positioning", t, flags=re.I):
        technologies.append("gnss")

    if "antenna" in t or re.search(r"\bant\.\s*(?:pin|pins)|u\.?fl", t, flags=re.I):
        technologies.append("antenna")

    if re.search(r"sensor|pressure|humidity|temperature|airflow|hall|imu|ahrs|motion|gas", t):
        technologies.append("sensor")
    if re.search(r"ssd|nvme|msata|cfast|satadom|flash storage", t):
        technologies.append("storage")
    if re.search(r"oled|tft|display|hmi", t):
        technologies.append("display")
    if re.search(r"rtc|oscillator|crystal|tcxo|ocxo|timing", t):
        technologies.append("timing")

    cellular_class = _first([
        ("5G RedCap", r"\bredcap\b"),
        ("Cat 1bis", r"cat\.?\s*1bis|cat1bis"),
        ("Cat 4", r"cat\.?\s*4\b"),
        ("Cat 1", r"cat\.?\s*1\b"),
        ("LPWA", r"lte-?m|nb-?iot|lpwa"),
    ], cellular_text)

    region = _first([
        ("Global", r"\bglobal\b|worldwide"),
        ("Americas", r"americas|north america|usa|u\.s\.|canada"),
        ("EMEA/APAC", r"emea|apac|europe/asia|europe.*asia"),
    ], t)

    # Many catalog part numbers use a standalone "-WW-" token for worldwide variants.
    # Apply this only to the part number token, not arbitrary description text.
    pn = (part_number or "").upper()
    if region is None and re.search(r"(?:^|-)WW(?:-|$)", pn):
        region = "Global"

    has_gnss = True if "gnss" in technologies else None
    if re.search(r"\bno\s+gnss\b|modem\s+only", t):
        has_gnss = False

    gnss_precision = None
    if re.search(r"\brtk\b|high precision|centimeter|centimetre|all-band", t):
        gnss_precision = "cm"
    elif has_gnss:
        gnss_precision = "standard"

    wifi_generation = _wifi_generation(text)
    has_bluetooth = True if "bluetooth" in technologies else None

    architecture = _first([
        ("open", r"open[- ]?cpu"),
        ("uconnect", r"u-?connectxpress|u-?connect|at command"),
        ("host", r"host[- ]?based"),
        ("standalone", r"stand[- ]?alone|standalone"),
    ], t)

    has_internal_antenna = bool(re.search(
        r"pcb\s*ant\.?|pcb[- ]?antenna|integrated antenna|internal antenna|int\.?\s*antenna|embedded antenna",
        t,
        flags=re.I,
    ))
    has_external_antenna = bool(re.search(
        r"external antenna|antenna[- ]?pin|antenna pin|ant\.\s*pin|ant\.\s*pins|u\.?fl",
        t,
        flags=re.I,
    ))

    if has_internal_antenna and has_external_antenna:
        antenna = "both"
    elif has_internal_antenna:
        antenna = "internal"
    elif has_external_antenna:
        antenna = "external"
    else:
        antenna = None

    form_factor = _first([
        ("Mini PCIe", r"mini\s*pci[eE]?"),
        ("M.2", r"\bm\.?2\b"),
        ("LGA", r"\blga\b"),
        ("LCC", r"\blcc\b"),
        ("SMD", r"\bsmd\b"),
    ], text)

    temp_min, temp_max = _temperature(text)

    certifications = []
    for label, pattern in [
        ("FCC", r"\bfcc\b"),
        ("ISED", r"\bised\b"),
        ("CE/RED", r"\bred\b|\bce\b"),
        ("Anatel", r"\banatel\b"),
        ("US MNO", r"\bmno cert"),
    ]:
        if re.search(pattern, t, flags=re.I):
            certifications.append(label)

    low_power_positive = bool(re.search(
        r"\blow[- ]?power\b|\bultra[- ]?low[- ]?power\b|\bbattery[- ]?powered\b|\blong battery\b|\blpwa\b|\blte-?m\b|\bnb-?iot\b",
        t,
        flags=re.I,
    ))

    # Explicit negative phrases must override generic low-power wording.
    low_power_negative = bool(re.search(
        r"\bw/?o\s+low[- ]?power\b|\bwithout\s+low[- ]?power\b|\bno\s+low[- ]?power\b|\blow[- ]?power\s+not\s+supported\b",
        t,
        flags=re.I,
    ))
    if low_power_negative:
        low_power_positive = False

    raw = {
        "text_length": len(text),
        "source": "deterministic_regex_v3.0-universal-engineering",
        "low_power_positive": low_power_positive,
        "low_power_negative": low_power_negative,
    }

    engineering_text = " ".join([category or "", description or "", *tags])
    engineering = extract_engineering_features(category, engineering_text)
    if engineering:
        raw["engineering"] = engineering

    antenna_applications, antenna_bands, antenna_active = _antenna_catalog_profile(text, category)
    if antenna_applications:
        raw["antenna_applications"] = antenna_applications
    if antenna_bands:
        raw["antenna_bands"] = antenna_bands
    if antenna_active is not None:
        raw["antenna_active"] = antenna_active

    # Capacitor-specific extraction is deliberately scoped to capacitor
    # products to prevent values such as 5 V or 100 nF from unrelated boards
    # being interpreted as the requested component rating.
    is_capacitor = (
        "capacitor" in category_l
        or "capacitor" in t
        or "kondensator" in t
        or "passivecap" in t
    )
    if is_capacitor:
        capacitance_uf = _capacitance_uf(text)
        capacitor_voltage_v = _capacitor_voltage_v(text)
        capacitor_tolerance_pct = _capacitor_tolerance_pct(text)
        capacitor_technology = _capacitor_technology(text)
        capacitor_mounting = _capacitor_mounting(text)
        capacitor_case_size = _capacitor_case_size(text)
        capacitor_esr_ohm = _capacitor_esr_ohm(text)
        capacitor_ripple_current_a = _capacitor_ripple_current_a(text)
        capacitor_lifetime_h = _capacitor_lifetime_h(text)

        if capacitance_uf is not None:
            raw["capacitance_uf"] = capacitance_uf
        if capacitor_voltage_v is not None:
            raw["capacitor_voltage_v"] = capacitor_voltage_v
        if capacitor_tolerance_pct is not None:
            raw["capacitor_tolerance_pct"] = capacitor_tolerance_pct
        if capacitor_technology:
            raw["capacitor_technology"] = capacitor_technology
        if capacitor_mounting:
            raw["capacitor_mounting"] = capacitor_mounting
        if capacitor_case_size:
            raw["capacitor_case_size"] = capacitor_case_size
        if capacitor_esr_ohm is not None:
            raw["capacitor_esr_ohm"] = capacitor_esr_ohm
        if capacitor_ripple_current_a is not None:
            raw["capacitor_ripple_current_a"] = capacitor_ripple_current_a
        if capacitor_lifetime_h is not None:
            raw["capacitor_lifetime_h"] = capacitor_lifetime_h

        if capacitance_uf is not None and capacitor_voltage_v is not None:
            # Ideal stored energy at rated voltage. This is a theoretical
            # comparison value, not a usable-energy guarantee.
            raw["capacitor_theoretical_energy_j"] = (
                0.5 * capacitance_uf * 1e-6 * capacitor_voltage_v ** 2
            )

    return {
        "technologies": sorted(set(technologies)),
        "cellular_class": cellular_class,
        "region": region,
        "has_gnss": has_gnss,
        "gnss_precision": gnss_precision,
        "wifi_generation": wifi_generation,
        "has_bluetooth": has_bluetooth,
        "architecture": architecture,
        "antenna": antenna,
        "form_factor": form_factor,
        "temperature_min": temp_min,
        "temperature_max": temp_max,
        "certifications": certifications,
        "raw_features": raw,
    }

def feature_values_for_model(extracted: dict) -> dict:
    return {
        "technologies_json": json.dumps(extracted.get("technologies", []), ensure_ascii=False),
        "cellular_class": extracted.get("cellular_class"),
        "region": extracted.get("region"),
        "has_gnss": extracted.get("has_gnss"),
        "gnss_precision": extracted.get("gnss_precision"),
        "wifi_generation": extracted.get("wifi_generation"),
        "has_bluetooth": extracted.get("has_bluetooth"),
        "architecture": extracted.get("architecture"),
        "antenna": extracted.get("antenna"),
        "form_factor": extracted.get("form_factor"),
        "temperature_min": extracted.get("temperature_min"),
        "temperature_max": extracted.get("temperature_max"),
        "certifications_json": json.dumps(extracted.get("certifications", []), ensure_ascii=False),
        "raw_features_json": json.dumps(extracted.get("raw_features", {}), ensure_ascii=False),
    }
