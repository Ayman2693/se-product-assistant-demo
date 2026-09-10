import json
import re
from typing import Any

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
        "source": "deterministic_regex_v2.4",
        "low_power_positive": low_power_positive,
        "low_power_negative": low_power_negative,
    }

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
