from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EngineeringFieldSpec:
    key: str
    label: str
    question: str
    kind: str = "number"  # number | enum | text | bool
    unit: str = ""
    comparison: str = "exact"  # exact | min | max | covers_min | covers_max | contains
    priority: int = 60
    weight: int = 14
    choices: tuple[tuple[str, str], ...] = ()


# The field library is deliberately category-agnostic. Categories select a
# subset below. Adding a new product family should normally mean updating this
# schema rather than writing a new matching engine.
FIELD_LIBRARY: dict[str, EngineeringFieldSpec] = {
    # Shared electrical / mechanical
    "frequency_hz": EngineeringFieldSpec(
        "frequency_hz", "Frequency", "What frequency do you need?", "number", "Hz", "exact", 100, 24
    ),
    "supply_voltage_v": EngineeringFieldSpec(
        "supply_voltage_v", "Supply voltage", "What supply voltage does your design use?", "number", "V", "exact", 76, 14
    ),
    "rated_voltage_v": EngineeringFieldSpec(
        "rated_voltage_v", "Voltage rating", "What minimum voltage rating is required?", "number", "V", "min", 80, 16
    ),
    "rated_current_a": EngineeringFieldSpec(
        "rated_current_a", "Rated current", "What minimum current rating is required?", "number", "A", "min", 86, 18
    ),
    "current_rating_a": EngineeringFieldSpec(
        "current_rating_a", "Current rating", "What minimum current rating is required?", "number", "A", "min", 84, 18
    ),
    "interface": EngineeringFieldSpec(
        "interface", "Interface", "Which electrical or host interface do you need?", "enum", "", "contains", 90, 18,
        (
            ("I²C", "i2c"), ("SPI", "spi"), ("UART", "uart"), ("USB", "usb"),
            ("PCIe", "pcie"), ("SDIO", "sdio"), ("CAN", "can"), ("Ethernet", "ethernet"),
            ("SATA", "sata"), ("NVMe", "nvme"), ("MIPI", "mipi"), ("LVDS", "lvds"),
            ("RGB", "rgb"), ("Analog", "analog"), ("Digital", "digital"),
        ),
    ),
    "mounting": EngineeringFieldSpec(
        "mounting", "Mounting", "Which mounting style do you need?", "enum", "", "exact", 55, 10,
        (("SMD / SMT", "smd"), ("Through-hole / THT", "tht")),
    ),
    "package": EngineeringFieldSpec(
        "package", "Package / form factor", "Do you have a package or form-factor requirement?", "enum", "", "exact", 48, 10
    ),
    "temperature_min_c": EngineeringFieldSpec(
        "temperature_min_c", "Minimum operating temperature", "What minimum operating temperature must the product support?", "number", "°C", "covers_min", 45, 8
    ),
    "temperature_max_c": EngineeringFieldSpec(
        "temperature_max_c", "Maximum operating temperature", "What maximum operating temperature must the product support?", "number", "°C", "covers_max", 45, 8
    ),

    # Timing / crystals / oscillators
    "load_capacitance_pf": EngineeringFieldSpec(
        "load_capacitance_pf", "Load capacitance", "What load capacitance does the crystal require?", "number", "pF", "exact", 96, 20
    ),
    "frequency_tolerance_ppm": EngineeringFieldSpec(
        "frequency_tolerance_ppm", "Frequency tolerance", "What maximum frequency tolerance is acceptable?", "number", "ppm", "max", 90, 18
    ),
    "frequency_stability_ppm": EngineeringFieldSpec(
        "frequency_stability_ppm", "Frequency stability", "What maximum frequency stability error is acceptable?", "number", "ppm", "max", 88, 18
    ),
    "esr_ohm": EngineeringFieldSpec(
        "esr_ohm", "ESR", "What maximum ESR is acceptable?", "number", "Ω", "max", 78, 14
    ),
    "drive_level_uw": EngineeringFieldSpec(
        "drive_level_uw", "Drive level", "What crystal drive level is required?", "number", "µW", "min", 62, 10
    ),
    "oscillator_type": EngineeringFieldSpec(
        "oscillator_type", "Oscillator type", "Which oscillator type do you need?", "enum", "", "exact", 92, 18,
        (("XO", "xo"), ("TCXO", "tcxo"), ("VCXO", "vcxo"), ("OCXO", "ocxo")),
    ),
    "output_type": EngineeringFieldSpec(
        "output_type", "Clock output", "Which clock-output standard do you need?", "enum", "", "exact", 90, 18,
        (("LVCMOS / CMOS", "lvcmos"), ("LVDS", "lvds"), ("HCSL", "hcsl"), ("Clipped sine", "clipped_sine"), ("Sine wave", "sine")),
    ),
    "phase_jitter_ps": EngineeringFieldSpec(
        "phase_jitter_ps", "Phase jitter", "What maximum phase jitter is acceptable?", "number", "ps", "max", 82, 16
    ),
    "timing_function": EngineeringFieldSpec(
        "timing_function", "Timing function", "Which timing function do you need?", "enum", "", "exact", 94, 18,
        (("Network synchronizer", "network_sync"), ("Jitter cleaner", "jitter_cleaner"), ("Clock buffer", "clock_buffer"), ("Clock generator", "clock_generator"), ("RTC", "rtc")),
    ),

    # Magnetics / EMC
    "choke_type": EngineeringFieldSpec(
        "choke_type", "Choke type", "Which choke type do you need?", "enum", "", "exact", 100, 22,
        (("Common-mode choke", "common_mode"), ("Power choke", "power"), ("EMI suppression choke", "suppression"), ("Saturation choke", "saturation")),
    ),
    "inductance_uh": EngineeringFieldSpec(
        "inductance_uh", "Inductance", "What inductance do you need?", "number", "µH", "exact", 96, 20
    ),
    "dc_resistance_ohm": EngineeringFieldSpec(
        "dc_resistance_ohm", "DC resistance", "What maximum DC resistance is acceptable?", "number", "Ω", "max", 80, 14
    ),
    "impedance_ohm": EngineeringFieldSpec(
        "impedance_ohm", "Impedance", "What minimum impedance do you need?", "number", "Ω", "min", 84, 16
    ),
    "test_frequency_hz": EngineeringFieldSpec(
        "test_frequency_hz", "Test frequency", "At which frequency should the impedance/filter requirement apply?", "number", "Hz", "exact", 70, 12
    ),
    "filter_type": EngineeringFieldSpec(
        "filter_type", "Filter type", "Which EMC / EMI filter type do you need?", "enum", "", "exact", 90, 18,
        (("Common-mode", "common_mode"), ("Feed-through", "feedthrough"), ("LC / pi", "lc_pi"), ("Mains / line", "line")),
    ),
    "cutoff_frequency_hz": EngineeringFieldSpec(
        "cutoff_frequency_hz", "Cutoff frequency", "What cutoff frequency do you need?", "number", "Hz", "exact", 76, 14
    ),
    "attenuation_db": EngineeringFieldSpec(
        "attenuation_db", "Attenuation", "What minimum attenuation is required?", "number", "dB", "min", 70, 12
    ),

    # Relays / contactors / switches / connectors
    "relay_type": EngineeringFieldSpec(
        "relay_type", "Relay type", "Which relay type do you need?", "enum", "", "exact", 92, 18,
        (("Power relay", "power"), ("Signal relay", "signal"), ("Reed relay", "reed"), ("Solid-state relay", "solid_state"), ("Latching relay", "latching")),
    ),
    "contact_form": EngineeringFieldSpec(
        "contact_form", "Contact form", "Which contact form do you need?", "enum", "", "exact", 90, 18,
        (("SPST", "spst"), ("SPDT", "spdt"), ("DPST", "dpst"), ("DPDT", "dpdt"), ("1 Form A", "1a"), ("1 Form C", "1c"), ("2 Form C", "2c")),
    ),
    "coil_voltage_v": EngineeringFieldSpec(
        "coil_voltage_v", "Coil voltage", "What coil voltage does your design use?", "number", "V", "exact", 88, 18
    ),
    "contact_current_a": EngineeringFieldSpec(
        "contact_current_a", "Contact current", "What minimum contact current is required?", "number", "A", "min", 92, 20
    ),
    "contact_voltage_v": EngineeringFieldSpec(
        "contact_voltage_v", "Contact voltage", "What minimum switched/contact voltage is required?", "number", "V", "min", 84, 16
    ),
    "switch_type": EngineeringFieldSpec(
        "switch_type", "Switch type", "Which switch type do you need?", "enum", "", "exact", 94, 18,
        (("Tactile", "tactile"), ("Toggle", "toggle"), ("Slide", "slide"), ("DIP", "dip"), ("Rotary", "rotary"), ("Rocker", "rocker"), ("Pushbutton", "pushbutton")),
    ),
    "poles": EngineeringFieldSpec(
        "poles", "Poles", "How many poles do you need?", "number", "", "exact", 78, 14
    ),
    "positions": EngineeringFieldSpec(
        "positions", "Positions / contacts", "How many positions or contacts do you need?", "number", "", "exact", 78, 14
    ),
    "connector_type": EngineeringFieldSpec(
        "connector_type", "Connector type", "Which connector type do you need?", "enum", "", "exact", 96, 20,
        (("Board-to-board", "board_to_board"), ("Wire-to-board", "wire_to_board"), ("FPC / FFC", "fpc"), ("USB", "usb"), ("RJ45", "rj45"), ("Terminal block", "terminal"), ("Circular", "circular")),
    ),
    "pitch_mm": EngineeringFieldSpec(
        "pitch_mm", "Pitch", "What connector pitch do you need?", "number", "mm", "exact", 90, 18
    ),

    # Displays
    "display_size_in": EngineeringFieldSpec(
        "display_size_in", "Display size", "What display diagonal do you need?", "number", "in", "exact", 96, 20
    ),
    "resolution": EngineeringFieldSpec(
        "resolution", "Resolution", "What display resolution do you need?", "text", "", "exact", 94, 20
    ),
    "touch": EngineeringFieldSpec(
        "touch", "Touch", "Does the display need touch functionality?", "bool", "", "exact", 84, 14,
        (("Touch required", "true"), ("No touch required", "false")),
    ),

    # Storage / computing
    "storage_capacity_gb": EngineeringFieldSpec(
        "storage_capacity_gb", "Storage capacity", "What minimum storage capacity do you need?", "number", "GB", "min", 98, 22
    ),
    "storage_interface": EngineeringFieldSpec(
        "storage_interface", "Storage interface", "Which storage interface do you need?", "enum", "", "exact", 94, 20,
        (("NVMe / PCIe", "nvme"), ("SATA", "sata"), ("mSATA", "msata"), ("eMMC", "emmc"), ("SD / microSD", "sd"), ("USB", "usb")),
    ),
    "cpu_arch": EngineeringFieldSpec(
        "cpu_arch", "CPU architecture", "Which CPU architecture do you need?", "enum", "", "exact", 92, 18,
        (("ARM", "arm"), ("x86 / x86-64", "x86"), ("RISC-V", "riscv")),
    ),
    "ram_gb": EngineeringFieldSpec(
        "ram_gb", "RAM", "What minimum RAM capacity do you need?", "number", "GB", "min", 86, 16
    ),
    "onboard_storage_gb": EngineeringFieldSpec(
        "onboard_storage_gb", "On-board storage", "What minimum on-board storage do you need?", "number", "GB", "min", 74, 14
    ),
    "ethernet_speed_mbps": EngineeringFieldSpec(
        "ethernet_speed_mbps", "Ethernet speed", "What minimum Ethernet speed do you need?", "number", "Mbit/s", "min", 72, 12
    ),

    # Sensors
    "sensor_type": EngineeringFieldSpec(
        "sensor_type", "Sensor type", "Which sensing function do you need?", "enum", "", "exact", 96, 20
    ),
    "pressure_range_kpa": EngineeringFieldSpec(
        "pressure_range_kpa", "Pressure range", "What maximum pressure range must the sensor cover?", "number", "kPa", "min", 98, 22
    ),
    "accuracy_pct": EngineeringFieldSpec(
        "accuracy_pct", "Accuracy", "What maximum measurement error is acceptable?", "number", "%", "max", 90, 18
    ),
    "force_range_n": EngineeringFieldSpec(
        "force_range_n", "Force range", "What maximum force must the sensor measure?", "number", "N", "min", 98, 22
    ),
    "airflow_range_lpm": EngineeringFieldSpec(
        "airflow_range_lpm", "Airflow range", "What maximum airflow must the sensor measure?", "number", "L/min", "min", 96, 20
    ),
    "humidity_max_pct": EngineeringFieldSpec(
        "humidity_max_pct", "Humidity range", "What maximum relative humidity must the sensor measure?", "number", "%RH", "min", 94, 18
    ),
    "measurement_temp_min_c": EngineeringFieldSpec(
        "measurement_temp_min_c", "Measurement minimum", "What is the lowest temperature that must be measured?", "number", "°C", "covers_min", 90, 18
    ),
    "measurement_temp_max_c": EngineeringFieldSpec(
        "measurement_temp_max_c", "Measurement maximum", "What is the highest temperature that must be measured?", "number", "°C", "covers_max", 90, 18
    ),
    "temperature_accuracy_c": EngineeringFieldSpec(
        "temperature_accuracy_c", "Temperature accuracy", "What maximum temperature error is acceptable?", "number", "°C", "max", 86, 16
    ),
    "axes": EngineeringFieldSpec(
        "axes", "Axes", "How many measurement axes do you need?", "number", "", "min", 88, 16
    ),
    "accel_range_g": EngineeringFieldSpec(
        "accel_range_g", "Acceleration range", "What acceleration range do you need?", "number", "g", "min", 86, 16
    ),
    "gyro_range_dps": EngineeringFieldSpec(
        "gyro_range_dps", "Gyroscope range", "What gyroscope range do you need?", "number", "°/s", "min", 84, 16
    ),
    "gas_type": EngineeringFieldSpec(
        "gas_type", "Gas / air-quality target", "Which gas or air-quality parameter do you need to detect?", "enum", "", "exact", 96, 20,
        (("CO₂", "co2"), ("CO", "co"), ("VOC", "voc"), ("NO₂", "no2"), ("O₂", "o2"), ("Air quality / multi-gas", "air_quality")),
    ),

    # Audio / haptics
    "audio_interface": EngineeringFieldSpec(
        "audio_interface", "Audio interface", "Which audio interface do you need?", "enum", "", "exact", 90, 18,
        (("I²S", "i2s"), ("TDM", "tdm"), ("PCM", "pcm"), ("Analog", "analog")),
    ),
    "sample_rate_khz": EngineeringFieldSpec(
        "sample_rate_khz", "Sample rate", "What minimum audio sample rate do you need?", "number", "kHz", "min", 76, 14
    ),
    "vibration_type": EngineeringFieldSpec(
        "vibration_type", "Haptic actuator type", "Which vibration / haptic actuator type do you need?", "enum", "", "exact", 90, 18,
        (("ERM", "erm"), ("LRA", "lra"), ("Piezo", "piezo")),
    ),
}


# Every currently configured SE catalog category has a profile. Existing
# dedicated qualification (wireless, antennas, capacitors) remains authoritative;
# these profiles add data-driven discrimination when the catalog exposes it.
CATEGORY_PROFILES: dict[str, tuple[str, ...]] = {
    # Cellular / wireless / GNSS
    "LTE-M / NB-IoT": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "LTE": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "5G RedCap": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Cellular Evaluation": ("interface", "supply_voltage_v"),
    "Standard GNSS": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "High Precision GNSS": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "GNSS Timing": ("interface", "frequency_hz", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Dead Reckoning": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "GNSS Evaluation": ("interface", "supply_voltage_v"),
    "Bluetooth LE": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Multiradio": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Wi-Fi": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Bluetooth Classic + LE": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Short Range Evaluation": ("interface", "supply_voltage_v"),

    # Antenna / RF
    "External Antennas": ("frequency_hz", "package", "temperature_min_c", "temperature_max_c"),
    "SMD Antennas": ("frequency_hz", "mounting", "package", "temperature_min_c", "temperature_max_c"),
    "Embedded Antennas": ("frequency_hz", "package", "temperature_min_c", "temperature_max_c"),
    "Other RF Components": ("frequency_hz", "rated_power_w", "package", "temperature_min_c", "temperature_max_c"),

    # Computing / memory
    "Computer on Modules": ("cpu_arch", "ram_gb", "onboard_storage_gb", "interface", "ethernet_speed_mbps", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Single Board Computer": ("cpu_arch", "ram_gb", "onboard_storage_gb", "interface", "ethernet_speed_mbps", "supply_voltage_v", "temperature_min_c", "temperature_max_c"),
    "Embedded Peripherals": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Flash Storage": ("storage_capacity_gb", "storage_interface", "package", "temperature_min_c", "temperature_max_c"),

    # Displays
    "TFT Displays": ("display_size_in", "resolution", "interface", "touch", "supply_voltage_v", "temperature_min_c", "temperature_max_c"),
    "OLED Displays": ("display_size_in", "resolution", "interface", "touch", "supply_voltage_v", "temperature_min_c", "temperature_max_c"),
    "Character Displays": ("resolution", "interface", "supply_voltage_v", "temperature_min_c", "temperature_max_c"),
    "Graphic Displays": ("display_size_in", "resolution", "interface", "touch", "supply_voltage_v", "temperature_min_c", "temperature_max_c"),
    "Smart Displays": ("display_size_in", "resolution", "interface", "touch", "supply_voltage_v", "temperature_min_c", "temperature_max_c"),
    "Display Driver IC": ("interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),

    # Audio / passives
    "Vibration": ("vibration_type", "supply_voltage_v", "rated_current_a", "package", "temperature_min_c", "temperature_max_c"),
    "Audio Codecs": ("audio_interface", "sample_rate_khz", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Capacitors": ("package", "temperature_min_c", "temperature_max_c"),

    # Electromechanical / EMC
    "Relays": ("relay_type", "contact_form", "coil_voltage_v", "contact_current_a", "contact_voltage_v", "mounting", "temperature_min_c", "temperature_max_c"),
    "Contactors": ("coil_voltage_v", "contact_current_a", "contact_voltage_v", "poles", "temperature_min_c", "temperature_max_c"),
    "Switches": ("switch_type", "poles", "positions", "contact_current_a", "contact_voltage_v", "mounting", "temperature_min_c", "temperature_max_c"),
    "Connectors": ("connector_type", "pitch_mm", "positions", "current_rating_a", "rated_voltage_v", "mounting", "temperature_min_c", "temperature_max_c"),
    "Chokes": ("choke_type", "inductance_uh", "rated_current_a", "dc_resistance_ohm", "impedance_ohm", "test_frequency_hz", "mounting", "temperature_min_c", "temperature_max_c"),
    "EMI / EMC Filters": ("filter_type", "cutoff_frequency_hz", "rated_current_a", "rated_voltage_v", "attenuation_db", "mounting", "temperature_min_c", "temperature_max_c"),
    "EMI Accessories": ("mounting", "package", "temperature_min_c", "temperature_max_c"),

    # Sensors
    "Motion Sensors": ("sensor_type", "axes", "accel_range_g", "gyro_range_dps", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Pressure Sensors": ("pressure_range_kpa", "accuracy_pct", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Force Sensors": ("force_range_n", "accuracy_pct", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Airflow Sensors": ("airflow_range_lpm", "accuracy_pct", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Humidity Sensors": ("humidity_max_pct", "accuracy_pct", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Temperature Sensors": ("measurement_temp_min_c", "measurement_temp_max_c", "temperature_accuracy_c", "interface", "supply_voltage_v", "package"),
    "Hall / Magnetic Sensors": ("sensor_type", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Gas Sensors": ("gas_type", "accuracy_pct", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),

    # Timing
    "RTCs": ("frequency_hz", "frequency_tolerance_ppm", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Oscillators": ("frequency_hz", "oscillator_type", "output_type", "supply_voltage_v", "frequency_stability_ppm", "phase_jitter_ps", "mounting", "package", "temperature_min_c", "temperature_max_c"),
    "Timing IC": ("timing_function", "frequency_hz", "output_type", "interface", "supply_voltage_v", "package", "temperature_min_c", "temperature_max_c"),
    "Crystals": ("frequency_hz", "load_capacitance_pf", "frequency_tolerance_ppm", "frequency_stability_ppm", "esr_ohm", "drive_level_uw", "mounting", "package", "temperature_min_c", "temperature_max_c"),
    "Timing Evaluation": ("interface", "supply_voltage_v"),
}

# Extra field used by RF profiles. It is appended after the mapping so the
# primary field library above remains easy to scan.
FIELD_LIBRARY["rated_power_w"] = EngineeringFieldSpec(
    "rated_power_w", "RF power rating", "What minimum RF power rating is required?", "number", "W", "min", 74, 14
)


def profile_for_category(category: str | None) -> tuple[EngineeringFieldSpec, ...]:
    keys = CATEGORY_PROFILES.get(category or "", ())
    return tuple(FIELD_LIBRARY[key] for key in keys if key in FIELD_LIBRARY)


def field_spec(key: str) -> EngineeringFieldSpec | None:
    return FIELD_LIBRARY.get(key)


def profile_status() -> dict[str, Any]:
    return {
        "categories": len(CATEGORY_PROFILES),
        "fields": len(FIELD_LIBRARY),
        "category_profiles": {category: list(fields) for category, fields in CATEGORY_PROFILES.items()},
    }
