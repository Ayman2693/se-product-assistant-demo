import re
from typing import Any

from app.services.engineering_features import parse_engineering_requirements

def _uniq(values):
    return list(dict.fromkeys(values))


_CAP_UF_FACTORS = {
    "pf": 1e-6,
    "nf": 1e-3,
    "uf": 1.0,
    "µf": 1.0,
    "μf": 1.0,
    "mf": 1e3,
    "f": 1e6,
}


def _num(value: str) -> float:
    return float(value.replace(",", "."))


def _parse_capacitance_uf(text: str) -> float | None:
    m = re.search(
        r"(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)\s*(pF|nF|uF|µF|μF|mF|F)\b",
        text,
        re.I,
    )
    return _num(m.group(1)) * _CAP_UF_FACTORS[m.group(2).lower()] if m else None


def _parse_capacitor_voltage_v(text: str) -> float | None:
    # A user phrase such as "for 12 V" is treated as a minimum required
    # voltage capability. The matcher may therefore select 16 V, 25 V, etc.
    m = re.search(
        r"(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)\s*v\b",
        text,
        re.I,
    )
    return _num(m.group(1)) if m else None


def _parse_capacitor_tolerance_pct(text: str) -> float | None:
    m = re.search(r"(?:±|\+/-|\+-)\s*(\d+(?:[.,]\d+)?)\s*%", text, re.I)
    return _num(m.group(1)) if m else None


def _parse_capacitor_esr_ohm(text: str) -> float | None:
    m = re.search(
        r"(?:\besr\b|equivalent\s+series\s+resistance)"
        r"[^0-9]{0,16}(?:max(?:imum)?\s*)?(\d+(?:[.,]\d+)?)\s*(mohm|mω|mΩ|ohm|ω|Ω)",
        text,
        re.I,
    )
    if not m:
        return None
    value = _num(m.group(1))
    return value / 1000.0 if m.group(2).lower().startswith("m") else value


def _parse_capacitor_ripple_current_a(text: str) -> float | None:
    m = re.search(
        r"(?:ripple\s*current|ripple|rippelstrom)"
        r"[^0-9]{0,16}(?:min(?:imum)?\s*)?(\d+(?:[.,]\d+)?)\s*(ma|a)\b",
        text,
        re.I,
    )
    if not m:
        return None
    value = _num(m.group(1))
    return value / 1000.0 if m.group(2).lower() == "ma" else value


def _parse_capacitor_lifetime_h(text: str) -> int | None:
    m = re.search(
        r"(?:life(?:time)?|load\s+life|service\s+life|lebensdauer)"
        r"[^0-9]{0,16}(?:min(?:imum)?\s*)?(\d{2,7})\s*(?:h|hours?|stunden)\b",
        text,
        re.I,
    )
    return int(m.group(1)) if m else None


def _parse_capacitor_temperature(text: str) -> tuple[float | None, float | None]:
    m = re.search(
        r"(-?\d{1,3})\s*(?:°\s*c)?\s*(?:to|\.\.\.|…|-)\s*\+?(-?\d{1,3})\s*°\s*c\b",
        text,
        re.I,
    )
    if not m:
        return None, None
    lo, hi = float(m.group(1)), float(m.group(2))
    if -100 <= lo <= 200 and -100 <= hi <= 200 and lo <= hi:
        return lo, hi
    return None, None


def interpret_text(text: str) -> dict[str, Any]:
    """
    Deterministic natural-language -> structured technical requirements.
    This is intentionally rule-based so product specs are not invented.
    An LLM can later be plugged in ahead of this layer with schema validation.
    """
    raw = text or ""
    t = raw.lower()

    out: dict[str, Any] = {
        "application": None,
        "product_domain": None,
        "catalog_category": None,
        "generic_interface": None,
        "technologies": [],
        "cellular_class": None,
        "region": None,
        "architecture": None,
        "antenna": None,
        "wifi_generation": [],
        "gnss_precision": None,
        "low_power": None,
        "host_interface": None,
        "antenna_connector": None,
        "antenna_count": None,
        "antenna_application": None,
        "antenna_band": None,
        "antenna_active": None,
        "bluetooth_required": None,
        "bluetooth_version_min": None,
        "max_footprint_mm2": None,
        "form_factor": None,
        "gnss_dual_band": None,

        "engineering_requirements": {},
        "answered_engineering_fields": [],

        # Capacitor-specific requirements.
        "capacitance_uf": None,
        "capacitor_voltage_v": None,
        "capacitor_tolerance_pct": None,
        "capacitor_tolerance_open": False,
        "capacitor_technology": None,
        "capacitor_mounting": None,
        "capacitor_case_size": None,
        "capacitor_esr_max_ohm": None,
        "capacitor_ripple_current_min_a": None,
        "capacitor_lifetime_min_h": None,
        "capacitor_temperature_min_c": None,
        "capacitor_temperature_max_c": None,
        "capacitor_energy_min_j": None,
    }
    evidence: list[str] = []

    # Product-domain router
    # First determine what kind of SE product the customer is asking for.
    # This prevents a sensor/display/timing request from falling into a
    # connectivity-specific qualification flow.

    category_patterns = [
        ("sensors", "Pressure Sensors", r"\bpressure\s+(?:sensor|transducer)|\bbarometric\b|\bdrucksensor(?:en)?\b|\bdruckaufnehmer\b"),
        ("sensors", "Temperature Sensors", r"\btemperature\s+sensor|\btemperature\s+measurement|\bthermistor\b|\btemperatursensor(?:en)?\b|\btemperaturmessung\b"),
        ("sensors", "Humidity Sensors", r"\bhumidity\s+sensor|\brelative humidity\b|\bfeuchtigkeitssensor(?:en)?\b|\bluftfeuchtigkeit\b"),
        ("sensors", "Motion Sensors", r"\bmotion\s+sensor|\bimu\b|\baccelerometer\b|\bgyroscope\b|\bahrs\b|\bbewegungssensor(?:en)?\b|\bbeschleunigungssensor(?:en)?\b|\bgyroskop\b"),
        ("sensors", "Force Sensors", r"\bforce\s+sensor|\bload\s+cell\b|\bstrain\s+(?:sensor|gauge)\b|\bkraftsensor(?:en)?\b|\bwägezelle(?:n)?\b|\bwaegezelle(?:n)?\b"),
        ("sensors", "Airflow Sensors", r"\bair\s*flow\s+sensor|\bairflow\s+sensor|\bmass\s+flow\b|\bdurchflusssensor(?:en)?\b|\bluftstromsensor(?:en)?\b"),
        ("sensors", "Hall / Magnetic Sensors", r"\bhall\s+(?:effect\s+)?sensor|\bmagnetic\s+sensor|\bmagnetometer\b|\bhall[- ]?sensor(?:en)?\b|\bmagnetfeldsensor(?:en)?\b"),
        ("sensors", "Gas Sensors", r"\bgas\s+sensor|\bco2\s+sensor|\bair quality sensor\b|\bgassensor(?:en)?\b|\bluftqualitätssensor(?:en)?\b|\bluftqualitaetssensor(?:en)?\b"),

        ("display", "TFT Displays", r"\btft\b|\btft[- ]?(?:display|anzeige|bildschirm)\b"),
        ("display", "OLED Displays", r"\boled\b|\boled[- ]?(?:display|anzeige|bildschirm)\b"),
        ("display", "Character Displays", r"\bcharacter\s+display\b"),
        ("display", "Graphic Displays", r"\bgraphic\s+display\b"),
        ("display", "Smart Displays", r"\bsmart\s+display\b|\bhmi\s+display\b"),
        ("display", "Display Driver IC", r"\bdisplay\s+driver\b"),

        ("storage", "Flash Storage", r"\bflash\s+storage\b|\bssd\b|\bnvme\b|\bmsata\b|\bcfast\b|\bsatadom\b"),
        (
            "computing",
            "Computer on Modules",
            r"\bcomputer[- ]on[- ]modules?\b|\bcom\b.*\bmodule\b|\bsmarc\b|\bcom\s*express\b|\bqseven\b|\brechnermodul(?:e)?\b",
        ),
        (
            "computing",
            "Single Board Computer",
            r"\bsingle[- ]board\s+computers?\b|\bsbc\b|\bpico[- ]?itx\b|\beinplatinenrechner\b",
        ),
        (
            "computing",
            "Embedded Peripherals",
            r"\bembedded\s+peripherals?\b|\bembedded[- ]?peripherie\b",
        ),

        ("timing", "RTCs", r"\breal[- ]time\s+clock\b|\brtc\b|\bechtzeituhr(?:en)?\b"),
        ("timing", "Oscillators", r"\boscillator\b|\btcxo\b|\bocxo\b|\bvcxo\b|\boszillator(?:en)?\b"),
        ("timing", "Crystals", r"\bquartz\s+crystal\b|\bcrystal\b|\bquarz(?:kristall)?(?:e)?\b"),
        ("timing", "Timing IC", r"\btiming\s+ic\b|\bclock\s+(?:generator|buffer|jitter)\b"),

        ("antenna", "External Antennas", r"\bexternal\s+antenna\b|\bsma\s+antenna\b|\bexterne\s+antenne(?:n)?\b"),
        ("antenna", "SMD Antennas", r"\bsmd\s+antenna\b|\bchip\s+antenna\b|\bsmd[- ]?antenne(?:n)?\b|\bchip[- ]?antenne(?:n)?\b"),
        ("antenna", "Embedded Antennas", r"\bembedded\s+antenna\b|\bpcb\s+antenna\b|\beingebettete\s+antenne(?:n)?\b|\bleiterplattenantenne(?:n)?\b"),

        ("audio_haptics", "Vibration", r"\bvibration\b|\bhaptic\b"),
        ("audio_haptics", "Audio Codecs", r"\baudio\s+codec\b"),

        ("components", "Capacitors", r"\bcapacitors?\b|\bkondensator(?:en)?\b"),
        ("components", "Relays", r"\brelays?\b|\brelais\b"),
        ("components", "Contactors", r"\bcontactors?\b|\bschütz(?:e)?\b|\bschuetz(?:e)?\b"),
        ("components", "Switches", r"\bswitch(?:es)?\b|\bschalter\b"),
        ("components", "Connectors", r"\bconnectors?\b|\bsteckverbinder\b"),
        ("components", "Chokes", r"\bchokes?\b|\bdrossel(?:n)?\b"),
        ("components", "EMI / EMC Filters", r"\bemi\b.*\bfilter\b|\bemc\b.*\bfilter\b|\bemv\b.*\bfilter\b"),
        ("components", "EMI Accessories", r"\bemi\s+accessor(?:y|ies)\b|\bemv[- ]?zubehör\b|\bemv[- ]?zubehoer\b"),
    ]

    for domain, category, pattern in category_patterns:
        if re.search(pattern, t, re.I):
            out["product_domain"] = domain
            out["catalog_category"] = category
            evidence.append(f"product_domain:{domain}")
            evidence.append(f"catalog_category:{category}")
            break

    if out["product_domain"] is None:
        if re.search(r"\bsensor\b|\bsensing\b|\bsensorik\b|\bsensoren?\b", t, re.I):
            out["product_domain"] = "sensors"
        elif re.search(r"\bdisplay\b|\bhmi\b|\bscreen\b|\banzeige\b|\bbildschirm\b", t, re.I):
            out["product_domain"] = "display"
        elif re.search(r"\bstorage\b|\bmemory\b|\bflash\b|\bspeicher\b|\bdatenspeicher\b", t, re.I):
            out["product_domain"] = "storage"
        elif re.search(r"\btiming\b|\bclock\b|\btakt(?:ung)?\b|\bzeitgeber\b", t, re.I):
            out["product_domain"] = "timing"
        elif re.search(r"\bantenna\b|\bantenne(?:n)?\b", t, re.I):
            out["product_domain"] = "antenna"
        elif re.search(
            r"\bcomputing\b|\bembedded computer\b|\bcomputer module\b|\bcomputer\b|"
            r"\bsbc\b|\brechnermodul\b|\bembedded[- ]?rechner\b|\brechner\b",
            t,
            re.I,
        ):
            out["product_domain"] = "computing"
        elif re.search(
            r"\bcomponents?\b|\bpassive components?\b|\bbauteil(?:e)?\b|\bkomponent(?:e|en)\b|\bemc\b|\bemi\b|\bemv\b",
            t,
            re.I,
        ):
            out["product_domain"] = "components"

    # Standalone antenna requirements.
    if out["product_domain"] == "antenna":
        app_hits = []
        if re.search(r"\bgnss\b|\bgps\b|\bgalileo\b|\bglonass\b|\bbeidou\b", t, re.I):
            app_hits.append("gnss")
        if re.search(r"wi-?fi|\bwlan\b|bluetooth|\bble\b", t, re.I):
            app_hits.append("wifi_bt")
        if re.search(r"\bcellular\b|\blte\b|\b5g\b|\b4g\b|\bgsm\b|\bumts\b|\blte-?m\b|\bnb-?iot\b", t, re.I):
            app_hits.append("cellular")
        if re.search(r"\blora\b|\bsigfox\b|\bism\b|\bsub[- ]?ghz\b|\b433\s*mhz\b|\b868\s*mhz\b|\b915\s*mhz\b", t, re.I):
            app_hits.append("ism")

        app_hits = _uniq(app_hits)
        if len(app_hits) >= 2:
            out["antenna_application"] = "multi"
        elif app_hits:
            out["antenna_application"] = app_hits[0]

        if out["antenna_application"]:
            evidence.append(f"antenna_application:{out['antenna_application']}")

        if out["antenna_application"] == "gnss":
            if re.search(r"dual[- ]band|multi[- ]band|\bl2\b|\bl5\b|\bl1\s*[/+]\s*l(?:2|5)\b", t, re.I):
                out["antenna_band"] = "gnss_multiband"
            elif re.search(r"\bl1\b|1559\s*[-–]\s*1609", t, re.I):
                out["antenna_band"] = "gnss_l1"

            if re.search(r"\bactive\b[^.;]{0,24}\b(?:gnss\s+)?(?:patch\s+)?antenna\b|\bactive\s+gnss\b", t, re.I):
                out["antenna_active"] = True
            elif re.search(r"\bpassive\b[^.;]{0,24}\b(?:gnss\s+)?(?:patch\s+)?antenna\b|\bpassive\s+gnss\b", t, re.I):
                out["antenna_active"] = False

        elif out["antenna_application"] == "wifi_bt":
            if re.search(r"wi-?fi\s*6e|\b6e\b|\b6\s*ghz\b", t, re.I):
                out["antenna_band"] = "wifi_6e"
            elif re.search(r"2[.,]4\s*(?:\+|/|and)\s*5\s*ghz|dual[- ]band\s+wi-?fi", t, re.I):
                out["antenna_band"] = "wifi_245"
            elif re.search(r"\b2[.,]4\s*ghz\b", t, re.I):
                out["antenna_band"] = "wifi_24"

        if out["antenna_band"]:
            evidence.append(f"antenna_band:{out['antenna_band']}")
        if out["antenna_active"] is not None:
            evidence.append(f"antenna_active:{out['antenna_active']}")

    # Generic electrical / host interface. This can be useful outside
    # connectivity as well, for example for digital sensors.
    interface_patterns = [
        ("i2c", r"\bi2c\b|\bi²c\b"),
        ("spi", r"\bspi\b"),
        ("uart", r"\buart\b"),
        ("usb", r"\busb\b"),
        ("sdio", r"\bsdio\b"),
        ("pcie", r"\bpcie\b|\bpci express\b"),
        ("analog", r"\banalog(?:ue)?\s+(?:output|interface)|\b4\s*-\s*20\s*ma\b|\b0\s*-\s*10\s*v\b"),
        ("digital", r"\bdigital\s+(?:output|interface)\b"),
    ]
    for value, pattern in interface_patterns:
        if re.search(pattern, t, re.I):
            out["generic_interface"] = value
            evidence.append(f"generic_interface:{value}")
            break

    # Application / use case
    app_patterns = [
        ("asset tracking", r"\basset\s+track|tracker|tracking|pallet|container tracking|logistics?|\bnachverfolgung\b|\bobjektverfolgung\b|\basset[- ]?tracking\b"),
        ("industrial gateway", r"industrial gateway|\bgateway\b|edge gateway|\bindustrie[- ]?gateway\b"),
        ("industrial IoT", r"industrial iot|iiot|factory automation|\bindustrie\s*4\.0\b|\bfabrikautomation\b|\bindustrieautomation\b"),
        ("agriculture / precision farming", r"agricultur|agriculture|agricultural|agri[- ]?(?:tech|culture)?|argecltural|precision farming|precision agriculture|\bfarming\b|\bfarm\b|tractor guidance|\blandwirtschaft\b|\bpräzisionslandwirtschaft\b|\bpraezisionslandwirtschaft\b"),
        ("robotics / autonomous", r"\brobot|agv|amr|autonomous|drone|\brobotik\b|\bautonom(?:e|es|er)?\b"),
        ("metering", r"smart meter|metering|\bsmart[- ]?meter\b|\bzähler\b|\bzaehler\b"),
        ("medical / wearable", r"medical|wearable|health|\bmedizin(?:isch)?\b|\bgesundheit\b"),
        ("display / HMI", r"\bhmi\b|display"),
        ("industrial storage", r"\bssd\b|nvme|industrial storage"),
    ]
    for value, pattern in app_patterns:
        if re.search(pattern, t, re.I):
            out["application"] = value
            evidence.append(f"application:{value}")
            break

    # Capacitor engineering requirements.
    if out["catalog_category"] == "Capacitors":
        capacitance = _parse_capacitance_uf(raw)
        if capacitance is not None:
            out["capacitance_uf"] = capacitance
            evidence.append(f"capacitance_uf:{capacitance}")

        voltage = _parse_capacitor_voltage_v(raw)
        if voltage is not None:
            out["capacitor_voltage_v"] = voltage
            evidence.append(f"capacitor_voltage_v:{voltage}")

        tolerance = _parse_capacitor_tolerance_pct(raw)
        if tolerance is not None:
            out["capacitor_tolerance_pct"] = tolerance
            evidence.append(f"capacitor_tolerance_pct:{tolerance}")

        if re.search(r"\bsuper\s*cap(?:acitor)?\b|\bsupercapacitor\b|\bultracap\b|\bedlc\b", t, re.I):
            out["capacitor_technology"] = "Supercapacitor"
        elif re.search(r"\btantal", t, re.I) and re.search(r"\bpolymer\b", t, re.I):
            out["capacitor_technology"] = "Tantalum polymer"
        elif re.search(r"\btantal", t, re.I):
            out["capacitor_technology"] = "Tantalum"
        elif re.search(r"\bceramic\b|\bmlcc\b|\bkeramik\b|\bx7r\b|\bx5r\b|\bc0g\b|\bnp0\b|\by5v\b", t, re.I):
            out["capacitor_technology"] = "Ceramic"
        elif re.search(r"\bfilm\b|\bpolypropylene\b|\bpolyester\b|\bfolie", t, re.I):
            out["capacitor_technology"] = "Film"
        elif re.search(r"\balumin(?:um|ium)\b.*\bpolymer\b", t, re.I):
            out["capacitor_technology"] = "Aluminum polymer"
        elif re.search(r"\balumin(?:um|ium)\b.*\belectrolytic\b|\belko\b|\belektrolyt", t, re.I):
            out["capacitor_technology"] = "Aluminum electrolytic"
        elif re.search(r"\bpolymer\b", t, re.I):
            out["capacitor_technology"] = "Polymer"

        if out["capacitor_technology"]:
            evidence.append(f"capacitor_technology:{out['capacitor_technology']}")

        if re.search(r"\bthrough[- ]?hole\b|\btht\b|\bradial\b|\baxial\b|\bleaded\b", t, re.I):
            out["capacitor_mounting"] = "Through-hole"
        elif re.search(r"\bsmd\b|\bsmt\b|\bsurface[- ]?mount\b", t, re.I):
            out["capacitor_mounting"] = "SMD"
        if out["capacitor_mounting"]:
            evidence.append(f"capacitor_mounting:{out['capacitor_mounting']}")

        m_case = re.search(r"(?<![A-Za-z0-9])(0201|0402|0603|0805|1206|1210|1812|2220)(?![A-Za-z0-9])", raw, re.I)
        if m_case:
            out["capacitor_case_size"] = m_case.group(1)
            evidence.append(f"capacitor_case_size:{out['capacitor_case_size']}")

        esr = _parse_capacitor_esr_ohm(raw)
        if esr is not None:
            out["capacitor_esr_max_ohm"] = esr
            evidence.append(f"capacitor_esr_max_ohm:{esr}")

        ripple = _parse_capacitor_ripple_current_a(raw)
        if ripple is not None:
            out["capacitor_ripple_current_min_a"] = ripple
            evidence.append(f"capacitor_ripple_current_min_a:{ripple}")

        lifetime = _parse_capacitor_lifetime_h(raw)
        if lifetime is not None:
            out["capacitor_lifetime_min_h"] = lifetime
            evidence.append(f"capacitor_lifetime_min_h:{lifetime}")

        temp_lo, temp_hi = _parse_capacitor_temperature(raw)
        if temp_lo is not None and temp_hi is not None:
            out["capacitor_temperature_min_c"] = temp_lo
            out["capacitor_temperature_max_c"] = temp_hi
            evidence.append(f"capacitor_temperature:{temp_lo}:{temp_hi}")

        # Energy is useful mainly for pulse/hold-up/supercapacitor use cases.
        # Do not infer it from capacitance+voltage in the customer request;
        # only capture an explicitly requested joule value.
        m_energy = re.search(
            r"(?:energy|stored\s+energy|energie)[^0-9]{0,12}(\d+(?:[.,]\d+)?)\s*(mj|j)\b",
            raw,
            re.I,
        )
        if m_energy:
            energy = _num(m_energy.group(1))
            if m_energy.group(2).lower() == "mj":
                energy /= 1000.0
            out["capacitor_energy_min_j"] = energy
            evidence.append(f"capacitor_energy_min_j:{energy}")

    # Technologies
    technologies = []
    if re.search(r"wi-?fi|wifi|wlan|802\.11|\bfunknetz\b", t, re.I):
        technologies.append("wifi")
        evidence.append("technology:wifi")
    if re.search(r"bluetooth|\bble\b|\bbt\s*\d|\bbt\s*/\s*ble", t, re.I):
        technologies.append("bluetooth")
        evidence.append("technology:bluetooth")
    if re.search(r"\bgnss\b|\bgps\b|\brtk\b|positioning|galileo|glonass|beidou|\bpositionierung\b|\bortung\b", t, re.I):
        technologies.append("gnss")
        evidence.append("technology:gnss")
    if re.search(r"cellular|lte-?m|nb-?iot|cat\.?\s*(?:1bis|1|4)|redcap|4g|5g|\bmobilfunk\b", t, re.I):
        technologies.append("cellular")
        evidence.append("technology:cellular")

    if out["product_domain"] == "sensors" or re.search(r"\bsensor\b|\bsensing\b|\bsensorik\b|\bsensoren?\b", t, re.I):
        technologies.append("sensor")
        evidence.append("technology:sensor")
    if out["product_domain"] == "storage":
        technologies.append("storage")
        evidence.append("technology:storage")
    if out["product_domain"] == "display":
        technologies.append("display")
        evidence.append("technology:display")
    if out["product_domain"] == "timing":
        technologies.append("timing")
        evidence.append("technology:timing")
    if out["product_domain"] == "antenna":
        technologies.append("antenna")
        evidence.append("technology:antenna")

    out["technologies"] = _uniq(technologies)

    # Antenna wording is often a requirement of a wireless module, not the
    # requested product domain itself.
    #
    # "Wi-Fi 6 module with external antenna" -> Connectivity
    # "external antenna for Wi-Fi"           -> Antenna
    wireless = set(out["technologies"])
    if (
        out["product_domain"] == "antenna"
        and wireless & {"wifi", "bluetooth", "cellular", "gnss"}
        and re.search(r"\bmodule?\b|\bmodul(?:e)?\b|\bdevice\b|\bgerät\b|\bgeraet\b", t, re.I)
    ):
        out["product_domain"] = "connectivity"
        out["catalog_category"] = None
        out["technologies"] = [tech for tech in out["technologies"] if tech != "antenna"]
        evidence.append("product_domain:connectivity")

    # Connectivity / positioning domain is derived only after product-centric
    # domains above had a chance to claim the request.
    if out["product_domain"] is None:
        wireless = set(out["technologies"])
        if wireless & {"wifi", "bluetooth", "cellular"}:
            out["product_domain"] = "connectivity"
            evidence.append("product_domain:connectivity")
        elif "gnss" in wireless:
            out["product_domain"] = "positioning"
            evidence.append("product_domain:positioning")

    # Cellular
    if re.search(r"redcap", t, re.I):
        out["cellular_class"] = "5G RedCap"
    elif re.search(r"cat\.?\s*1bis|cat1bis|cat-1bis", t, re.I):
        out["cellular_class"] = "Cat 1bis"
    elif re.search(r"cat\.?\s*4\b|cat4\b", t, re.I):
        out["cellular_class"] = "Cat 4"
    elif re.search(r"lte-?m|nb-?iot|lpwa", t, re.I):
        out["cellular_class"] = "LPWA"

    if out["cellular_class"]:
        evidence.append(f"cellular_class:{out['cellular_class']}")

    # Region
    if re.search(r"\bglobal\b|worldwide|world wide|\bweltweit\b", t, re.I):
        out["region"] = "Global"
    elif re.search(r"americas|north america|\busa\b|united states|canada|\bnordamerika\b", t, re.I):
        out["region"] = "Americas"
    elif re.search(r"emea|apac|europe|germany|asia|\beuropa\b|\bdeutschland\b|\basien\b", t, re.I):
        out["region"] = "EMEA/APAC"
    if out["region"]:
        evidence.append(f"region:{out['region']}")

    # Architecture
    if re.search(r"host[- ]?based|host controlled|linux host|external host|\bhost[- ]?basiert\w*\b|\bhostgesteuert\w*\b", t, re.I):
        out["architecture"] = "host"
    elif re.search(r"open[- ]?cpu|open cpu|zephyr|application on module|\banwendung\s+auf\s+dem\s+modul\b", t, re.I):
        out["architecture"] = "open"
    elif re.search(r"u-?connectxpress|u-?connect|at command|at-command|\bat[- ]?befehle?\b", t, re.I):
        out["architecture"] = "uconnect"
    elif re.search(r"stand[- ]?alone|standalone|\beigenständig\b|\beigenstaendig\b", t, re.I):
        out["architecture"] = "standalone"
    if out["architecture"]:
        evidence.append(f"architecture:{out['architecture']}")

    # Antenna
    internal = bool(re.search(
        r"internal antenna|integrated antenna|pcb antenna|embedded antenna|"
        r"\bintern(?:e|en|er|es)?\s+antenne(?:n)?\b|"
        r"\bintegriert(?:e|en|er|es)?\s+antenne(?:n)?\b|"
        r"\bleiterplattenantenne(?:n)?\b",
        t,
        re.I,
    ))
    external = bool(re.search(
        r"external antenna|antenna pin|u\.?fl|ufl|sma|"
        r"\bextern(?:e|en|er|es)?\s+antenne(?:n)?\b|"
        r"\bantennenpin(?:s)?\b",
        t,
        re.I,
    ))
    if internal and external:
        out["antenna"] = "both"
    elif internal:
        out["antenna"] = "internal"
    elif external:
        out["antenna"] = "external"
    if out["antenna"]:
        evidence.append(f"antenna:{out['antenna']}")

    # Wi-Fi generation(s). Multiple acceptable generations can be supplied
    # in one sentence, e.g. "Wi-Fi 5 or Wi-Fi 6".
    wifi_generations: list[str] = []
    if re.search(r"wi-?fi[-\s]*4\b|wifi[-\s]*4\b|wlan[-\s]*4\b|802\.11n|802\.11bgn", t, re.I):
        wifi_generations.append("4")
    if re.search(r"wi-?fi[-\s]*5\b|wifi[-\s]*5\b|wlan[-\s]*5\b|802\.11ac", t, re.I):
        wifi_generations.append("5")
    if re.search(r"wi-?fi[-\s]*6\b|wifi[-\s]*6\b|wlan[-\s]*6\b|802\.11ax", t, re.I):
        wifi_generations.append("6")
    if re.search(r"wi-?fi[-\s]*6e|wifi[-\s]*6e|wlan[-\s]*6e|6\s*ghz", t, re.I):
        # 6E also contains "6", so remove the plain 6 only when the text
        # refers exclusively to 6E and not separately to Wi-Fi 6.
        explicit_plain_6 = bool(re.search(
            r"(?:wi-?fi|wifi|wlan)[-\s]*6\b(?!e)",
            t,
            re.I,
        ))
        if not explicit_plain_6:
            wifi_generations = [g for g in wifi_generations if g != "6"]
        wifi_generations.append("6E")

    out["wifi_generation"] = _uniq(wifi_generations)
    for generation in out["wifi_generation"]:
        evidence.append(f"wifi_generation:{generation}")

    # GNSS precision
    if re.search(r"\brtk\b|centimeter|centimetre|cm[- ]level|high precision|zentimeter|hochpräzis|hochpraezis", t, re.I):
        out["gnss_precision"] = "cm"
    elif re.search(r"standard gnss|meter[- ]level|metre[- ]level|normal gnss|metergenau|meterbereich", t, re.I):
        out["gnss_precision"] = "standard"
    if out["gnss_precision"]:
        evidence.append(f"gnss_precision:{out['gnss_precision']}")

    # Power
    if re.search(r"battery powered|battery-powered|low power|ultra low power|long battery|power efficient|batteriebetrieb|akkubetrieb|stromsparend|niedriger stromverbrauch", t, re.I):
        out["low_power"] = True
        evidence.append("low_power:true")
    elif re.search(r"mains powered|not battery|low power not important", t, re.I):
        out["low_power"] = False
        evidence.append("low_power:false")


    # Host interface
    has_sdio = bool(re.search(r"\bsdio\b", t, re.I))
    has_pcie = bool(re.search(r"\bpcie\b|\bpci express\b", t, re.I))
    if has_sdio and has_pcie:
        out["host_interface"] = "sdio_pcie"
    elif has_sdio:
        out["host_interface"] = "sdio"
    elif has_pcie:
        out["host_interface"] = "pcie"
    if out["host_interface"]:
        evidence.append(f"host_interface:{out['host_interface']}")

    # External antenna connector / count
    if re.search(r"\bu\.?fl\b|\bufl\b", t, re.I):
        out["antenna_connector"] = "ufl"
    elif re.search(r"antenna[- ]?pin|ant\.?\s*pins?|solder\s*pads?", t, re.I):
        out["antenna_connector"] = "antenna_pin"
    if out["antenna_connector"]:
        evidence.append(f"antenna_connector:{out['antenna_connector']}")

    m_ant_count = re.search(r"\b([1-4])\s*(?:x\s*)?(?:u\.?fl|antenna\s*pins?|ant\.?\s*pins?)\b", t, re.I)
    if m_ant_count:
        out["antenna_count"] = int(m_ant_count.group(1))
        evidence.append(f"antenna_count:{out['antenna_count']}")

    # Bluetooth requirement / minimum version
    m_bt = re.search(
        r"(?:bluetooth(?:\s+le)?|ble|bt(?:/ble)?)\s*(?:version\s*)?([4-6](?:\.\d+)?)",
        t,
        re.I,
    )
    if m_bt:
        out["bluetooth_required"] = True
        out["bluetooth_version_min"] = m_bt.group(1)
        evidence.append(f"bluetooth_version_min:{out['bluetooth_version_min']}")
    elif re.search(r"bluetooth\s+(?:is\s+)?required|need\s+(?:bluetooth|ble)", t, re.I):
        out["bluetooth_required"] = True
        evidence.append("bluetooth_required:true")

    # Mechanical form factor
    if re.search(r"\bmini\s*pci[eE]?\b", raw, re.I):
        out["form_factor"] = "Mini PCIe"
    elif re.search(r"\bm\.?2\b", raw, re.I):
        out["form_factor"] = "M.2"
    elif re.search(r"\blga\b", raw, re.I):
        out["form_factor"] = "LGA"
    elif re.search(r"\blcc\b", raw, re.I):
        out["form_factor"] = "LCC"
    if out["form_factor"]:
        evidence.append(f"form_factor:{out['form_factor']}")

    # Explicit maximum module footprint, e.g. "max 150 mm2"
    m_area = re.search(
        r"(?:max(?:imum)?|under|below|<=?|≤)\s*(\d+(?:\.\d+)?)\s*mm(?:2|²)",
        t,
        re.I,
    )
    if m_area:
        out["max_footprint_mm2"] = float(m_area.group(1))
        evidence.append(f"max_footprint_mm2:{out['max_footprint_mm2']}")

    # Dual-band GNSS
    if re.search(r"\bl1\s*\+\s*l5\b|dual[- ]band\s+gnss|dual[- ]frequency\s+gnss", t, re.I):
        out["gnss_dual_band"] = True
        evidence.append("gnss_dual_band:true")

    # Schema-driven engineering values for the selected catalog category.
    # These are normalized to the same units used for catalog products.
    engineering = parse_engineering_requirements(out.get("catalog_category"), raw)
    if engineering:
        out["engineering_requirements"] = engineering
        for key, value in engineering.items():
            evidence.append(f"engineering:{key}:{value}")

    return {
        "requirements": out,
        "evidence": evidence,
        "confidence": min(1.0, 0.35 + 0.08 * len(evidence)),
    }


def merge_requirements(current: dict[str, Any] | None, extracted: dict[str, Any]) -> dict[str, Any]:
    current = dict(current or {})
    for key, value in extracted.items():
        if value is None:
            continue
        if key in {"technologies", "wifi_generation", "answered_engineering_fields"}:
            if value:
                current[key] = _uniq([*(current.get(key) or []), *value])
        elif key == "engineering_requirements":
            merged_engineering = dict(current.get(key) or {})
            merged_engineering.update(value or {})
            current[key] = merged_engineering
        else:
            current[key] = value
    current.setdefault("technologies", [])
    current.setdefault("wifi_generation", [])
    current.setdefault("engineering_requirements", {})
    current.setdefault("answered_engineering_fields", [])
    return current


def missing_requirements(req: dict[str, Any]) -> list[str]:
    missing: list[str] = []

    domain = req.get("product_domain")
    if not domain:
        missing.append("product_domain")

    if domain == "connectivity":
        if not req.get("technologies"):
            missing.append("technologies")

        tech = set(req.get("technologies") or [])

        if "cellular" in tech:
            if not req.get("cellular_class"):
                missing.append("cellular_class")
            if not req.get("region"):
                missing.append("region")

        if "wifi" in tech:
            if not req.get("wifi_generation"):
                missing.append("wifi_generation")
            if not req.get("architecture"):
                missing.append("architecture")

        if "bluetooth" in tech and not req.get("architecture"):
            missing.append("architecture")

        if "gnss" in tech and not req.get("gnss_precision"):
            missing.append("gnss_precision")

    elif domain == "positioning":
        if not req.get("gnss_precision"):
            missing.append("gnss_precision")

    elif domain in {
        "sensors",
        "display",
        "storage",
        "timing",
        "antenna",
        "computing",
        "components",
        "audio_haptics",
    }:
        if not req.get("catalog_category"):
            missing.append("catalog_category")

        # A capacitor cannot be meaningfully selected from category alone.
        # Ask the high-value electrical questions first; advanced constraints
        # remain optional and are parsed when the customer supplies them.
        if domain == "antenna":
            if not req.get("antenna_application"):
                missing.append("antenna_application")
            if req.get("antenna_application") in {"gnss", "wifi_bt"} and not req.get("antenna_band"):
                missing.append("antenna_band")
            if req.get("antenna_application") == "gnss" and req.get("antenna_active") is None:
                missing.append("antenna_active")

        if req.get("catalog_category") == "Capacitors":
            if req.get("capacitance_uf") is None:
                missing.append("capacitance_uf")
            if req.get("capacitor_voltage_v") is None:
                missing.append("capacitor_voltage_v")
            if not req.get("capacitor_technology"):
                missing.append("capacitor_technology")
            if not req.get("capacitor_mounting"):
                missing.append("capacitor_mounting")
            if req.get("capacitor_tolerance_pct") is None and not req.get("capacitor_tolerance_open"):
                missing.append("capacitor_tolerance")

    return _uniq(missing)


QUESTION_MAP = {
    "product_domain": {
        "text": "Which SE product area best matches what you are looking for?",
        "options": [
            "Connectivity / wireless",
            "GNSS / positioning",
            "Sensors",
            "Antennas / RF",
            "Displays / HMI",
            "Storage",
            "Timing",
            "Embedded computing",
            "Components / EMC",
            "Audio / haptics",
        ],
    },
    "catalog_category": {
        "text": "Which product type is closest to your requirement?",
        "options": [],
    },
    "application": {
        "text": "What type of application or use case is this for?",
        "options": ["Asset tracking", "Industrial gateway", "Industrial IoT", "Agriculture / precision farming", "Robotics / autonomous", "Metering", "Medical / wearable"],
    },
    "technologies": {
        "text": "Which connectivity or positioning technologies are required?",
        "options": ["Wi-Fi", "Bluetooth LE", "Cellular", "GNSS", "Cellular + GNSS", "Wi-Fi + Bluetooth"],
    },
    "cellular_class": {
        "text": "Which cellular technology is required?",
        "options": ["LTE-M / NB-IoT", "LTE Cat 1bis", "LTE Cat 4", "5G RedCap"],
    },
    "region": {
        "text": "Where will the product be deployed?",
        "options": ["Global", "Americas", "Europe / EMEA / APAC"],
    },
    "wifi_generation": {
        "text": "Which Wi-Fi generations are acceptable? Select one or more.",
        "options": ["Wi-Fi 4", "Wi-Fi 5", "Wi-Fi 6", "Wi-Fi 6E"],
    },
    "capacitance_uf": {
        "text": "What capacitance do you need?",
        "options": ["100 nF", "1 µF", "10 µF", "47 µF", "100 µF"],
    },
    "capacitor_voltage_v": {
        "text": "What minimum voltage rating should the capacitor support?",
        "options": ["6.3 V", "10 V", "16 V", "25 V", "50 V", "100 V"],
    },
    "capacitor_technology": {
        "text": "Do you have a preferred capacitor technology?",
        "options": [
            "Ceramic / MLCC",
            "Tantalum",
            "Film",
            "Aluminum electrolytic",
            "Polymer",
            "Supercapacitor",
            "No preference",
        ],
    },
    "capacitor_mounting": {
        "text": "What mounting style do you need?",
        "options": ["SMD / SMT", "Through-hole", "No preference"],
    },
    "capacitor_tolerance": {
        "text": "Do you have a capacitance tolerance requirement?",
        "options": ["±5%", "±10%", "±20%", "No preference"],
    },
    "architecture": {
        "text": "How should the wireless solution be controlled?",
        "options": ["Host-based", "Open CPU", "u-connectXpress / AT commands", "Standalone"],
    },
    "gnss_precision": {
        "text": "What positioning accuracy class is required for your application?",
        "options": [
            "Standard positioning — meter-level accuracy",
            "High-precision positioning — centimeter-level RTK",
            "Accuracy not yet defined / open",
        ],
    },
}


def next_question(req: dict[str, Any]) -> dict[str, Any] | None:
    missing = missing_requirements(req)
    if not missing:
        return None
    key = missing[0]
    q = QUESTION_MAP.get(key)
    if not q:
        return None
    return {"key": key, **q}
