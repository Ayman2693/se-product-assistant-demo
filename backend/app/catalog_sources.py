CATALOG_BASE = "https://www.spezial.com"
CATALOG_PRODUCTS_PAGE = "/en/products/"

# Canonical catalog sections used by the assistant.
#
# `extra_paths` are additional listing roots that belong to the same canonical
# category. They are necessary when SE uses a child URL that does not share the
# configured parent prefix (for example /en/timkhz/ below /en/timxtal/).
#
# Products imported from an extra path keep the canonical parent category.
CATALOG_SOURCES = [
    # Wireless / RF — Cellular
    {"category": "LTE-M / NB-IoT", "path": "/en/cellpwa/"},
    {"category": "LTE", "path": "/en/cellte/"},
    {"category": "5G RedCap", "path": "/en/cell5gred/"},
    {"category": "Cellular Evaluation", "path": "/en/celeval/"},

    # Wireless / RF — Positioning
    {"category": "Standard GNSS", "path": "/en/posstdgnss/"},
    {"category": "High Precision GNSS", "path": "/en/poshpgnss/"},
    {"category": "GNSS Timing", "path": "/en/postime/"},
    {"category": "Dead Reckoning", "path": "/en/posdr/"},
    {"category": "GNSS Evaluation", "path": "/en/poseval/"},

    # Wireless / RF — Short Range
    {"category": "Bluetooth LE", "path": "/en/shoble/"},
    {"category": "Multiradio", "path": "/en/shomulti/"},
    {"category": "Wi-Fi", "path": "/en/showifi/"},
    {"category": "Bluetooth Classic + LE", "path": "/en/shobtcle/"},
    {"category": "Short Range Evaluation", "path": "/en/shoeval/"},

    # Wireless / RF — Antennas / RF
    {"category": "External Antennas", "path": "/en/antext/"},
    {"category": "SMD Antennas", "path": "/en/antsmd/"},
    {"category": "Embedded Antennas", "path": "/en/antemb/"},
    {"category": "Other RF Components", "path": "/en/rfother/"},

    # Computing
    {"category": "Computer on Modules", "path": "/en/com/"},
    {"category": "Single Board Computer", "path": "/en/sbc/"},
    {"category": "Embedded Peripherals", "path": "/en/memep/"},

    # Memory
    {"category": "Flash Storage", "path": "/en/memflash/"},

    # Displays
    {"category": "TFT Displays", "path": "/en/disp-tft/"},
    {"category": "OLED Displays", "path": "/en/disp-oled/"},
    {"category": "Character Displays", "path": "/en/dispcharacter/"},
    {"category": "Graphic Displays", "path": "/en/disp-graph/"},
    {"category": "Smart Displays", "path": "/en/disp-smart/"},
    {"category": "Display Driver IC", "path": "/en/disp-ic/"},

    # Audio
    {"category": "Vibration", "path": "/en/audiovibration/"},
    {"category": "Audio Codecs", "path": "/en/audocodec/"},

    # Passives
    {"category": "Capacitors", "path": "/en/passivecap/"},

    # Emech / EMI
    {"category": "Relays", "path": "/en/emechrelay/"},
    {"category": "Contactors", "path": "/en/emechcontactor/"},
    {"category": "Switches", "path": "/en/emechswitches/"},
    {"category": "Connectors", "path": "/en/emechconn/"},
    {
        "category": "Chokes",
        "path": "/en/emechchokes/",
        "extra_paths": [
            "/en/emechchokecurrent/",
            "/en/emechchokessuppres/",
            "/en/emechchokesatur/",
        ],
    },
    {"category": "EMI / EMC Filters", "path": "/en/emechfiters/"},
    {"category": "EMI Accessories", "path": "/en/filteracc/"},

    # Sensors
    {"category": "Motion Sensors", "path": "/en/sensingmotion/"},
    {"category": "Pressure Sensors", "path": "/en/sensingpressure/"},
    {"category": "Force Sensors", "path": "/en/sensingforce/"},
    {"category": "Airflow Sensors", "path": "/en/sensingairflow/"},
    {"category": "Humidity Sensors", "path": "/en/sensinghumid/"},
    {"category": "Temperature Sensors", "path": "/en/sensingtemp/"},
    {"category": "Hall / Magnetic Sensors", "path": "/en/sensinghall/"},
    {"category": "Gas Sensors", "path": "/en/sensinggas/"},

    # Timing
    {"category": "RTCs", "path": "/en/timrtc/"},
    {
        "category": "Oscillators",
        "path": "/en/timosc/",
        "extra_paths": [
            "/en/timoscmhz/",
            "/en/timosckhz/",
        ],
    },
    {
        "category": "Timing IC",
        "path": "/en/timic/",
        "extra_paths": [
            "/en/timicnetsync/",
            "/en/timicjittercleaner/",
            "/en/timicbuffer/",
        ],
    },
    {
        "category": "Crystals",
        "path": "/en/timxtal/",
        "extra_paths": [
            "/en/timxtalmhz/",
            "/en/timkhz/",
        ],
    },
    {"category": "Timing Evaluation", "path": "/en/timrtceval/"},
]


def source_seed_paths(source: dict) -> list[str]:
    """Return de-duplicated listing roots for one canonical catalog category."""
    paths = [source["path"], *(source.get("extra_paths") or [])]
    return list(dict.fromkeys(paths))
