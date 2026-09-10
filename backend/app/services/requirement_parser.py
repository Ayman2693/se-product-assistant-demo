import re
from typing import Any

def _uniq(values):
    return list(dict.fromkeys(values))

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
        "wifi_generation": None,
        "gnss_precision": None,
        "low_power": None,
        "host_interface": None,
        "antenna_connector": None,
        "antenna_count": None,
        "bluetooth_required": None,
        "bluetooth_version_min": None,
        "max_footprint_mm2": None,
        "form_factor": None,
        "gnss_dual_band": None,
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
        ("computing", "Computer on Modules", r"\bcomputer[- ]on[- ]module\b|\bcom\b.*\bmodule\b"),
        ("computing", "Single Board Computer", r"\bsingle[- ]board\s+computer\b|\bsbc\b"),

        ("timing", "RTCs", r"\breal[- ]time\s+clock\b|\brtc\b|\bechtzeituhr(?:en)?\b"),
        ("timing", "Oscillators", r"\boscillator\b|\btcxo\b|\bocxo\b|\bvcxo\b|\boszillator(?:en)?\b"),
        ("timing", "Crystals", r"\bquartz\s+crystal\b|\bcrystal\b|\bquarz(?:kristall)?(?:e)?\b"),
        ("timing", "Timing IC", r"\btiming\s+ic\b|\bclock\s+(?:generator|buffer|jitter)\b"),

        ("antenna", "External Antennas", r"\bexternal\s+antenna\b|\bsma\s+antenna\b|\bexterne\s+antenne(?:n)?\b"),
        ("antenna", "SMD Antennas", r"\bsmd\s+antenna\b|\bchip\s+antenna\b|\bsmd[- ]?antenne(?:n)?\b|\bchip[- ]?antenne(?:n)?\b"),
        ("antenna", "Embedded Antennas", r"\bembedded\s+antenna\b|\bpcb\s+antenna\b|\beingebettete\s+antenne(?:n)?\b|\bleiterplattenantenne(?:n)?\b"),

        ("audio_haptics", "Vibration", r"\bvibration\b|\bhaptic\b"),
        ("audio_haptics", "Audio Codecs", r"\baudio\s+codec\b"),

        ("components", "Capacitors", r"\bcapacitor\b"),
        ("components", "Relays", r"\brelay\b"),
        ("components", "Contactors", r"\bcontactor\b"),
        ("components", "Switches", r"\bswitch(?:es)?\b"),
        ("components", "Connectors", r"\bconnector\b"),
        ("components", "Chokes", r"\bchoke\b"),
        ("components", "EMI / EMC Filters", r"\bemi\b.*\bfilter\b|\bemc\b.*\bfilter\b"),
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
        elif re.search(r"\bembedded computer\b|\bcomputer module\b|\bsbc\b|\brechnermodul\b|\bembedded[- ]?rechner\b", t, re.I):
            out["product_domain"] = "computing"

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

    # Wi-Fi generation
    if re.search(r"wi-?fi[-\s]*6e|wifi[-\s]*6e|wlan[-\s]*6e|6\s*ghz", t, re.I):
        out["wifi_generation"] = "6E"
    elif re.search(r"wi-?fi[-\s]*6\b|wifi[-\s]*6\b|wlan[-\s]*6\b|802\.11ax", t, re.I):
        out["wifi_generation"] = "6"
    elif re.search(r"wi-?fi[-\s]*5\b|wifi[-\s]*5\b|wlan[-\s]*5\b|802\.11ac", t, re.I):
        out["wifi_generation"] = "5"
    elif re.search(r"wi-?fi[-\s]*4\b|wifi[-\s]*4\b|wlan[-\s]*4\b|802\.11n|802\.11bgn", t, re.I):
        out["wifi_generation"] = "4"
    if out["wifi_generation"]:
        evidence.append(f"wifi_generation:{out['wifi_generation']}")

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
        r"(?:bluetooth|ble|bt(?:/ble)?)\s*(?:version\s*)?([4-6](?:\.\d+)?)",
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
        if key == "technologies":
            if value:
                current[key] = _uniq([*(current.get(key) or []), *value])
        else:
            current[key] = value
    current.setdefault("technologies", [])
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
        "text": "Which Wi-Fi generation is required?",
        "options": ["Wi-Fi 4", "Wi-Fi 5", "Wi-Fi 6", "Wi-Fi 6E"],
    },
    "architecture": {
        "text": "How should the wireless solution be controlled?",
        "options": ["Host-based", "Open CPU", "u-connectXpress / AT commands", "Standalone"],
    },
    "gnss_precision": {
        "text": "What GNSS accuracy is required?",
        "options": ["Standard / meter-level", "Centimeter-level / RTK"],
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
