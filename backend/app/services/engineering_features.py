from __future__ import annotations

import json
import math
import re
from typing import Any

from app.services.engineering_profiles import EngineeringFieldSpec, field_spec, profile_for_category


def _norm(text: str | None) -> str:
    return (text or "").lower().replace("–", "-").replace("—", "-").replace("µ", "u").replace("μ", "u")


def _num(value: str) -> float:
    return float(value.replace(",", "."))


def _first_number(patterns: list[str], text: str) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                return _num(match.group(1))
            except (ValueError, IndexError):
                pass
    return None


def _unique_single(values: list[float], rel_tol: float = 1e-9) -> float | None:
    unique: list[float] = []
    for value in values:
        if not any(abs(value - other) <= max(abs(value), abs(other), 1.0) * rel_tol for other in unique):
            unique.append(value)
    return unique[0] if len(unique) == 1 else None


def _frequencies_hz(text: str) -> list[float]:
    values: list[float] = []
    factors = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
    for match in re.finditer(r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*(GHz|MHz|kHz|Hz)\b", text, re.I):
        try:
            values.append(_num(match.group(1)) * factors[match.group(2).lower()])
        except ValueError:
            continue
    return values


def _single_frequency_hz(text: str) -> float | None:
    return _unique_single(_frequencies_hz(text), rel_tol=1e-10)


def _interfaces(text: str) -> list[str]:
    t = _norm(text)
    patterns = [
        ("i2c", r"\bi2c\b|\bi²c\b"),
        ("spi", r"\bspi\b"),
        ("uart", r"\buart\b"),
        ("usb", r"\busb(?:\s*[23](?:\.\d)?)?\b"),
        ("pcie", r"\bpcie\b|\bpci\s*express\b"),
        ("sdio", r"\bsdio\b"),
        ("can", r"\bcan(?:\s*fd)?\b"),
        ("ethernet", r"\bethernet\b|\brmii\b|\brgmii\b"),
        ("sata", r"\bsata\b|\bmsata\b"),
        ("nvme", r"\bnvme\b"),
        ("mipi", r"\bmipi\b|\bdsi\b|\bcsi\b"),
        ("lvds", r"\blvds\b"),
        ("rgb", r"\brgb\b"),
        ("analog", r"\banalog(?:ue)?\b|\b4\s*-\s*20\s*ma\b|\b0\s*-\s*10\s*v\b"),
        ("digital", r"\bdigital\s+(?:output|interface)\b"),
    ]
    return [value for value, pattern in patterns if re.search(pattern, t, re.I)]


def _mounting(text: str) -> str | None:
    t = _norm(text)
    if re.search(r"\bthrough[- ]?hole\b|\btht\b|\baxial\b|\bradial\b|\bleaded\b", t):
        return "tht"
    if re.search(r"\bsmd\b|\bsmt\b|\bsurface[- ]?mount\b", t):
        return "smd"
    return None


def _package(text: str) -> str | None:
    patterns = [
        ("Mini PCIe", r"\bmini\s*pci[e]?\b"),
        ("M.2", r"\bm\.?2\b"),
        ("LGA", r"\blga\b"),
        ("LCC", r"\blcc\b"),
        ("BGA", r"\bbga\b"),
        ("QFN", r"\bqfn\b"),
        ("DFN", r"\bdfn\b"),
        ("SOIC", r"\bsoic\b"),
        ("TSSOP", r"\btssop\b"),
        ("SOT", r"\bsot[- ]?\d+\b"),
        ("DIP", r"\bdip\b"),
        ("SMD", r"\bsmd\b"),
    ]
    for value, pattern in patterns:
        if re.search(pattern, text, re.I):
            return value

    # Crystal / oscillator packages often appear as dimensions.
    match = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(?:[x×]\s*(\d+(?:[.,]\d+)?)\s*)?mm\b", text, re.I)
    if match:
        parts = [_num(match.group(1)), _num(match.group(2))]
        if match.group(3):
            parts.append(_num(match.group(3)))
        return "×".join(f"{value:g}" for value in parts) + " mm"
    return None


def _temperature_range(text: str) -> tuple[float | None, float | None]:
    patterns = [
        r"(?<![A-Za-z0-9])(-?\d{1,3})\s*/\s*\+?(-?\d{1,3})\s*°?\s*C\b",
        r"(?<![A-Za-z0-9])(-?\d{1,3})\s*(?:to|\.\.\.|…)\s*\+?(-?\d{1,3})\s*°?\s*C\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            lo, hi = float(match.group(1)), float(match.group(2))
            if -100 <= lo <= 200 and -100 <= hi <= 250 and lo <= hi:
                return lo, hi
    return None, None


def _voltage(text: str, *, context: str | None = None) -> float | None:
    if context:
        value = _first_number([
            rf"(?:{context})[^0-9]{{0,18}}([0-9]+(?:[.,][0-9]+)?)\s*v\b",
            rf"([0-9]+(?:[.,][0-9]+)?)\s*v\b[^.;]{{0,18}}(?:{context})",
        ], text)
        if value is not None:
            return value

    values = [_num(m.group(1)) for m in re.finditer(r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*v\b", text, re.I)]
    return _unique_single(values)


def _current_a(text: str, *, context: str | None = None) -> float | None:
    patterns = []
    if context:
        patterns.extend([
            rf"(?:{context})[^0-9]{{0,18}}([0-9]+(?:[.,][0-9]+)?)\s*(ma|a)\b",
            rf"([0-9]+(?:[.,][0-9]+)?)\s*(ma|a)\b[^.;]{{0,18}}(?:{context})",
        ])
    patterns.append(r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*(ma|a)\b")

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = _num(match.group(1))
            unit = match.group(2).lower()
            return value / 1000.0 if unit == "ma" else value
    return None


def _resistance_ohm(text: str, contexts: tuple[str, ...]) -> float | None:
    context = "|".join(contexts)
    for pattern in [
        rf"(?:{context})[^0-9]{{0,20}}([0-9]+(?:[.,][0-9]+)?)\s*(kohm|kω|kΩ|mohm|mω|mΩ|ohm|ω|Ω)\b",
        rf"([0-9]+(?:[.,][0-9]+)?)\s*(kohm|kω|kΩ|mohm|mω|mΩ|ohm|ω|Ω)\b[^.;]{{0,20}}(?:{context})",
    ]:
        match = re.search(pattern, text, re.I)
        if match:
            value = _num(match.group(1))
            unit = match.group(2).lower().replace("ω", "ohm").replace("Ω", "ohm")
            if unit.startswith("k"):
                return value * 1000.0
            if unit.startswith("m"):
                return value / 1000.0
            return value
    return None


def _inductance_uh(text: str) -> float | None:
    match = re.search(r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*(nh|uh|µh|μh|mh|h)\b", text, re.I)
    if not match:
        return None
    value = _num(match.group(1))
    unit = match.group(2).lower().replace("µ", "u").replace("μ", "u")
    factors = {"nh": 1e-3, "uh": 1.0, "mh": 1e3, "h": 1e6}
    return value * factors[unit]


def _ppm(text: str, context: str) -> float | None:
    patterns = [
        rf"(?:{context})[^0-9±+\-]{{0,24}}(?:±|\+/-|\+-)?\s*([0-9]+(?:[.,][0-9]+)?)\s*ppm\b",
        rf"(?:±|\+/-|\+-)\s*([0-9]+(?:[.,][0-9]+)?)\s*ppm\b[^.;]{{0,24}}(?:{context})",
    ]
    value = _first_number(patterns, text)
    if value is not None:
        return value
    return None


def _load_cap_pf(text: str) -> float | None:
    value = _first_number([
        r"(?:load\s*capacitance|load\s*cap|\bcl\b)[^0-9]{0,16}([0-9]+(?:[.,][0-9]+)?)\s*pf\b",
        r"([0-9]+(?:[.,][0-9]+)?)\s*pf\b[^.;]{0,18}(?:load\s*capacitance|\bcl\b)",
    ], text)
    if value is not None:
        return value
    # Crystal catalog cards often contain only one pF value and it is the load capacitance.
    values = [_num(m.group(1)) for m in re.finditer(r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*pf\b", text, re.I)]
    return _unique_single(values)


def _drive_level_uw(text: str) -> float | None:
    match = re.search(r"(?:drive\s*level)[^0-9]{0,16}([0-9]+(?:[.,][0-9]+)?)\s*(uw|µw|μw|mw)\b", text, re.I)
    if not match:
        return None
    value = _num(match.group(1))
    unit = match.group(2).lower().replace("µ", "u").replace("μ", "u")
    return value * 1000.0 if unit == "mw" else value


def _phase_jitter_ps(text: str) -> float | None:
    match = re.search(r"(?:phase\s*)?jitter[^0-9]{0,18}([0-9]+(?:[.,][0-9]+)?)\s*(fs|ps|ns)\b", text, re.I)
    if not match:
        return None
    value = _num(match.group(1))
    unit = match.group(2).lower()
    return value / 1000.0 if unit == "fs" else value * 1000.0 if unit == "ns" else value


def _enum(patterns: list[tuple[str, str]], text: str) -> str | None:
    for value, pattern in patterns:
        if re.search(pattern, text, re.I):
            return value
    return None


def _pressure_kpa(text: str) -> float | None:
    match = re.search(r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*(pa|kpa|mpa|bar|mbar|psi)\b", text, re.I)
    if not match:
        return None
    value = _num(match.group(1))
    unit = match.group(2).lower()
    factors = {"pa": 0.001, "kpa": 1.0, "mpa": 1000.0, "bar": 100.0, "mbar": 0.1, "psi": 6.894757}
    return value * factors[unit]


def _percentage(text: str, contexts: tuple[str, ...] = ()) -> float | None:
    context = "|".join(contexts)
    patterns = []
    if contexts:
        patterns.extend([
            rf"(?:{context})[^0-9]{{0,16}}(?:±|\+/-|\+-)?\s*([0-9]+(?:[.,][0-9]+)?)\s*%",
            rf"(?:±|\+/-|\+-)?\s*([0-9]+(?:[.,][0-9]+)?)\s*%[^.;]{{0,16}}(?:{context})",
        ])
    for pattern in patterns:
        value = _first_number([pattern], text)
        if value is not None:
            return value
    return None


def _force_n(text: str) -> float | None:
    match = re.search(r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*(mn|n|kn)\b", text, re.I)
    if not match:
        return None
    value = _num(match.group(1))
    unit = match.group(2).lower()
    factors = {"mn": 0.001, "n": 1.0, "kn": 1000.0}
    return value * factors[unit]


def _airflow_lpm(text: str) -> float | None:
    match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*(l/min|lpm|slm|sccm)\b", text, re.I)
    if not match:
        return None
    value = _num(match.group(1))
    unit = match.group(2).lower()
    return value / 1000.0 if unit == "sccm" else value


def _measurement_temp_range(text: str) -> tuple[float | None, float | None]:
    match = re.search(
        r"(?:measurement|measuring|sensing|range)[^.;]{0,30}?(-?\d{1,3})\s*(?:to|\.\.\.|…|-)\s*\+?(-?\d{1,3})\s*°?\s*c",
        text,
        re.I,
    )
    if match:
        lo, hi = float(match.group(1)), float(match.group(2))
        if lo <= hi:
            return lo, hi
    return None, None


def _temperature_accuracy(text: str) -> float | None:
    return _first_number([
        r"(?:temperature\s*)?(?:accuracy|error)[^0-9±]{0,16}(?:±|\+/-|\+-)?\s*([0-9]+(?:[.,][0-9]+)?)\s*°?\s*c",
    ], text)


def _storage_capacity_gb(text: str) -> float | None:
    values: list[float] = []
    for match in re.finditer(r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*(gb|tb)\b", text, re.I):
        value = _num(match.group(1))
        if match.group(2).lower() == "tb":
            value *= 1024.0
        values.append(value)
    return max(values) if values else None


def _display_size_in(text: str) -> float | None:
    return _first_number([
        r"([0-9]+(?:[.,][0-9]+)?)\s*(?:\"|inch|inches)\b",
        r"([0-9]+(?:[.,][0-9]+)?)\s*[- ]?inch\b",
    ], text)


def _resolution(text: str) -> str | None:
    match = re.search(r"(?<!\d)(\d{2,5})\s*[x×]\s*(\d{2,5})(?!\d)", text, re.I)
    return f"{match.group(1)}×{match.group(2)}" if match else None


def _touch(text: str) -> bool | None:
    t = _norm(text)
    if re.search(r"\bno\s+touch\b|\bnon[- ]?touch\b|\bwithout\s+touch\b", t):
        return False
    if re.search(r"\btouch\b|\btouchscreen\b|\bcapacitive\s+touch\b|\bresistive\s+touch\b", t):
        return True
    return None


def _axes(text: str) -> float | None:
    match = re.search(r"\b([1-9])\s*[- ]?axis\b", text, re.I)
    return float(match.group(1)) if match else None


def _accel_range_g(text: str) -> float | None:
    match = re.search(r"(?:±|\+/-|\+-)\s*([0-9]+(?:[.,][0-9]+)?)\s*g\b", text, re.I)
    return _num(match.group(1)) if match else None


def _gyro_range_dps(text: str) -> float | None:
    match = re.search(r"(?:±|\+/-|\+-)\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:dps|°/s|deg/s)\b", text, re.I)
    return _num(match.group(1)) if match else None


def _humidity_max(text: str) -> float | None:
    values = [_num(m.group(1)) for m in re.finditer(r"([0-9]+(?:[.,][0-9]+)?)\s*%\s*(?:rh)?\b", text, re.I)]
    return max(values) if values else None


def _sample_rate_khz(text: str) -> float | None:
    match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*(khz|ks/s|ksps)\b", text, re.I)
    return _num(match.group(1)) if match else None


def _ethernet_speed_mbps(text: str) -> float | None:
    values: list[float] = []
    for match in re.finditer(r"([0-9]+(?:[.,][0-9]+)?)\s*(mbit/s|mbps|gbit/s|gbps)\b", text, re.I):
        value = _num(match.group(1))
        if match.group(2).lower() in {"gbit/s", "gbps"}:
            value *= 1000.0
        values.append(value)
    if re.search(r"\bgigabit\s+ethernet\b|\b1gbe\b", text, re.I):
        values.append(1000.0)
    return max(values) if values else None


def _ram_gb(text: str) -> float | None:
    match = re.search(r"(?:ram|ddr[345]?|memory)[^.;]{0,18}?([0-9]+(?:[.,][0-9]+)?)\s*gb\b", text, re.I)
    return _num(match.group(1)) if match else None


def _onboard_storage_gb(text: str) -> float | None:
    match = re.search(r"(?:emmc|flash|storage|ssd)[^.;]{0,18}?([0-9]+(?:[.,][0-9]+)?)\s*(gb|tb)\b", text, re.I)
    if not match:
        return None
    value = _num(match.group(1))
    return value * 1024.0 if match.group(2).lower() == "tb" else value


def _extract_field(key: str, text: str, category: str) -> Any:
    t = _norm(text)

    if key == "frequency_hz":
        return _single_frequency_hz(text)
    if key == "supply_voltage_v":
        return _voltage(text, context=r"supply|vcc|vdd|input\s+voltage")
    if key == "rated_voltage_v":
        return _voltage(text, context=r"rated|working|contact|switch(?:ing)?|voltage")
    if key in {"rated_current_a", "current_rating_a"}:
        return _current_a(text, context=r"rated|current|load")
    if key == "interface":
        values = _interfaces(text)
        return values if values else None
    if key == "mounting":
        return _mounting(text)
    if key == "package":
        return _package(text)
    if key in {"temperature_min_c", "temperature_max_c"}:
        lo, hi = _temperature_range(text)
        return lo if key.endswith("min_c") else hi

    if key == "load_capacitance_pf":
        return _load_cap_pf(text)
    if key == "frequency_tolerance_ppm":
        value = _ppm(text, r"tolerance|initial\s+accuracy")
        if value is None:
            match = re.search(r"(?:±|\+/-|\+-)\s*([0-9]+(?:[.,][0-9]+)?)\s*ppm\b", text, re.I)
            return _num(match.group(1)) if match else None
        return value
    if key == "frequency_stability_ppm":
        return _ppm(text, r"stability|frequency\s+stability")
    if key == "esr_ohm":
        return _resistance_ohm(text, (r"\besr\b", r"equivalent\s+series\s+resistance"))
    if key == "drive_level_uw":
        return _drive_level_uw(text)
    if key == "oscillator_type":
        return _enum([
            ("ocxo", r"\bocxo\b"), ("tcxo", r"\btcxo\b"), ("vcxo", r"\bvcxo\b"), ("xo", r"\bxo\b|\boscillator\b"),
        ], text)
    if key == "output_type":
        return _enum([
            ("hcsl", r"\bhcsl\b"), ("lvds", r"\blvds\b"), ("lvcmos", r"\blvcmos\b|\bcmos\b"),
            ("clipped_sine", r"clipped\s+sine"), ("sine", r"\bsine(?:\s+wave)?\b"),
        ], text)
    if key == "phase_jitter_ps":
        return _phase_jitter_ps(text)
    if key == "timing_function":
        return _enum([
            ("network_sync", r"network\s+sync|synchroni[sz]er|sync[e]?"),
            ("jitter_cleaner", r"jitter\s+cleaner"),
            ("clock_buffer", r"clock\s+buffer|fanout\s+buffer"),
            ("clock_generator", r"clock\s+generator|frequency\s+synthesizer"),
            ("rtc", r"real[- ]time\s+clock|\brtc\b"),
        ], text)

    if key == "choke_type":
        return _enum([
            ("common_mode", r"common[- ]mode"), ("saturation", r"saturation\s+choke"),
            ("suppression", r"suppression\s+choke|emi\s+choke|noise\s+choke"),
            ("power", r"power\s+choke|storage\s+choke"),
        ], text)
    if key == "inductance_uh":
        return _inductance_uh(text)
    if key == "dc_resistance_ohm":
        return _resistance_ohm(text, (r"\bdcr\b", r"dc\s+resistance"))
    if key == "impedance_ohm":
        return _resistance_ohm(text, (r"impedance", r"\bz\b"))
    if key == "test_frequency_hz":
        match = re.search(r"(?:@|at)\s*([0-9]+(?:[.,][0-9]+)?)\s*(ghz|mhz|khz|hz)\b", text, re.I)
        if match:
            factors = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
            return _num(match.group(1)) * factors[match.group(2).lower()]
        return None
    if key == "filter_type":
        return _enum([
            ("common_mode", r"common[- ]mode"), ("feedthrough", r"feed[- ]?through"),
            ("lc_pi", r"\bpi\s+filter\b|\blc\s+filter\b"), ("line", r"line\s+filter|mains\s+filter"),
        ], text)
    if key == "cutoff_frequency_hz":
        match = re.search(r"(?:cut[- ]?off|corner)[^0-9]{0,16}([0-9]+(?:[.,][0-9]+)?)\s*(ghz|mhz|khz|hz)\b", text, re.I)
        if match:
            factors = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
            return _num(match.group(1)) * factors[match.group(2).lower()]
        return None
    if key == "attenuation_db":
        return _first_number([r"(?:attenuation|insertion\s+loss)[^0-9]{0,16}([0-9]+(?:[.,][0-9]+)?)\s*db\b"], text)

    if key == "relay_type":
        return _enum([
            ("solid_state", r"solid[- ]state|\bssr\b"), ("reed", r"reed\s+relay"),
            ("latching", r"latching|bistable"), ("signal", r"signal\s+relay"), ("power", r"power\s+relay"),
        ], text)
    if key == "contact_form":
        return _enum([
            ("spdt", r"\bspdt\b|\b1\s*form\s*c\b"), ("spst", r"\bspst\b|\b1\s*form\s*a\b"),
            ("dpdt", r"\bdpdt\b|\b2\s*form\s*c\b"), ("dpst", r"\bdpst\b"),
            ("2c", r"\b2\s*form\s*c\b"), ("1c", r"\b1\s*form\s*c\b"), ("1a", r"\b1\s*form\s*a\b"),
        ], text)
    if key == "coil_voltage_v":
        return _voltage(text, context=r"coil")
    if key == "contact_current_a":
        return _current_a(text, context=r"contact|switch(?:ing)?")
    if key == "contact_voltage_v":
        values = [
            _num(match.group(1))
            for match in re.finditer(
                r"(?<![A-Za-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*v\b",
                text,
                re.I,
            )
        ]
        return max(values) if values else None
    if key == "switch_type":
        return _enum([
            ("tactile", r"tact(?:ile)?\s+switch"), ("toggle", r"toggle\s+switch"),
            ("slide", r"slide\s+switch"), ("dip", r"\bdip\s+switch"),
            ("rotary", r"rotary\s+switch"), ("rocker", r"rocker\s+switch"),
            ("pushbutton", r"push[- ]?button|pushbutton"),
        ], text)
    if key == "poles":
        match = re.search(r"\b([1-9])\s*(?:pole|poles)\b", text, re.I)
        if match:
            return float(match.group(1))
        contact = _enum([("1", r"\bsp(?:st|dt)\b"), ("2", r"\bdp(?:st|dt)\b")], text)
        return float(contact) if contact else None
    if key == "positions":
        match = re.search(r"\b([0-9]{1,3})\s*(?:positions?|pos\.?|pins?|contacts?)\b", text, re.I)
        return float(match.group(1)) if match else None
    if key == "connector_type":
        return _enum([
            ("rj45", r"\brj45\b"), ("usb", r"\busb[- ]?(?:a|b|c|type[- ]?c)?\b"),
            ("fpc", r"\bfpc\b|\bffc\b"), ("terminal", r"terminal\s+block"),
            ("circular", r"circular\s+connector|\bm\d+\s+connector"),
            ("board_to_board", r"board[- ]to[- ]board"), ("wire_to_board", r"wire[- ]to[- ]board"),
        ], text)
    if key == "pitch_mm":
        return _first_number([r"(?:pitch|raster)[^0-9]{0,12}([0-9]+(?:[.,][0-9]+)?)\s*mm\b", r"([0-9]+(?:[.,][0-9]+)?)\s*mm\s+pitch\b"], text)

    if key == "display_size_in":
        return _display_size_in(text)
    if key == "resolution":
        return _resolution(text)
    if key == "touch":
        return _touch(text)

    if key == "storage_capacity_gb":
        return _storage_capacity_gb(text)
    if key == "storage_interface":
        return _enum([
            ("nvme", r"\bnvme\b|pcie\s+ssd"), ("msata", r"\bmsata\b"), ("sata", r"\bsata\b"),
            ("emmc", r"\bemmc\b"), ("sd", r"\bmicro\s*sd\b|\bsd\s+card\b"), ("usb", r"\busb\b"),
        ], text)
    if key == "cpu_arch":
        return _enum([("riscv", r"risc[- ]?v"), ("x86", r"\bx86(?:-64)?\b|intel\s+atom|intel\s+core|amd\s+ryzen"), ("arm", r"\barm\b|cortex[- ]?[am]\d+")], text)
    if key == "ram_gb":
        return _ram_gb(text)
    if key == "onboard_storage_gb":
        return _onboard_storage_gb(text)
    if key == "ethernet_speed_mbps":
        return _ethernet_speed_mbps(text)

    if key == "sensor_type":
        return _enum([
            ("imu", r"\bimu\b|inertial\s+measurement"), ("accelerometer", r"accelerometer|acceleration\s+sensor"),
            ("gyroscope", r"gyroscope|gyro\s+sensor"), ("magnetometer", r"magnetometer"),
            ("hall", r"hall[- ]?effect|hall\s+sensor"),
        ], text)
    if key == "pressure_range_kpa":
        return _pressure_kpa(text)
    if key == "accuracy_pct":
        return _percentage(text, (r"accuracy", r"error", r"tolerance"))
    if key == "force_range_n":
        return _force_n(text)
    if key == "airflow_range_lpm":
        return _airflow_lpm(text)
    if key == "humidity_max_pct":
        return _humidity_max(text)
    if key in {"measurement_temp_min_c", "measurement_temp_max_c"}:
        lo, hi = _measurement_temp_range(text)
        return lo if key.endswith("min_c") else hi
    if key == "temperature_accuracy_c":
        return _temperature_accuracy(text)
    if key == "axes":
        return _axes(text)
    if key == "accel_range_g":
        return _accel_range_g(text)
    if key == "gyro_range_dps":
        return _gyro_range_dps(text)
    if key == "gas_type":
        return _enum([
            ("co2", r"\bco2\b|carbon\s+dioxide"), ("no2", r"\bno2\b|nitrogen\s+dioxide"),
            ("o2", r"\bo2\b|oxygen"), ("voc", r"\bvoc\b|volatile\s+organic"),
            ("co", r"\bco\b|carbon\s+monoxide"), ("air_quality", r"air\s+quality|multi[- ]?gas"),
        ], text)

    if key == "audio_interface":
        return _enum([("i2s", r"\bi2s\b|\bi²s\b"), ("tdm", r"\btdm\b"), ("pcm", r"\bpcm\b"), ("analog", r"\banalog\b")], text)
    if key == "sample_rate_khz":
        return _sample_rate_khz(text)
    if key == "vibration_type":
        return _enum([("lra", r"\blra\b|linear\s+resonant"), ("erm", r"\berm\b|eccentric\s+rotating"), ("piezo", r"\bpiezo")], text)

    if key == "rated_power_w":
        match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*(mw|w)\b", text, re.I)
        if match:
            value = _num(match.group(1))
            return value / 1000.0 if match.group(2).lower() == "mw" else value
        return None

    return None


def extract_engineering_features(category: str | None, text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for spec in profile_for_category(category):
        value = _extract_field(spec.key, text, category or "")
        if value is not None and value != []:
            result[spec.key] = value
    return result


def parse_engineering_requirements(category: str | None, text: str) -> dict[str, Any]:
    """Parse explicit user values using the same normalized units as the catalog.

    Multi-valued catalog properties such as a product exposing I2C + SPI are
    useful for matching, but a customer sentence containing several interfaces
    is ambiguous (AND vs OR). Only a single explicit value is therefore promoted
    automatically; multi-valued intent is left for the adaptive conversation.
    """
    extracted = extract_engineering_features(category, text)
    parsed: dict[str, Any] = {}
    for key, value in extracted.items():
        if isinstance(value, list):
            if len(value) == 1:
                parsed[key] = value[0]
            continue
        parsed[key] = value
    return parsed


def engineering_signal(engineering: dict[str, Any], key: str) -> Any:
    value = engineering.get(key)
    if isinstance(value, list):
        # Multi-valued properties are safe for matching, but ambiguous for an
        # entropy-based single-choice question unless the product has one value.
        return value[0] if len(value) == 1 else None
    return value


def normalize_expected(spec: EngineeringFieldSpec, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if spec.kind == "bool":
        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "1", "required"}
        return bool(value)
    if spec.kind == "number":
        if isinstance(value, (int, float)):
            return float(value)

        raw = str(value)
        if spec.key in {"frequency_hz", "test_frequency_hz", "cutoff_frequency_hz"}:
            parsed = _single_frequency_hz(raw)
            if parsed is not None:
                return parsed
        elif spec.key in {"rated_current_a", "current_rating_a", "contact_current_a"}:
            parsed = _current_a(raw)
            if parsed is not None:
                return parsed
        elif spec.key == "inductance_uh":
            parsed = _inductance_uh(raw)
            if parsed is not None:
                return parsed
        elif spec.key in {"dc_resistance_ohm", "impedance_ohm", "esr_ohm"}:
            generic_resistance = re.search(
                r"([0-9]+(?:[.,][0-9]+)?)\s*(kohm|kω|kΩ|mohm|mω|mΩ|ohm|ω|Ω)\b",
                raw,
                re.I,
            )
            if generic_resistance:
                number = _num(generic_resistance.group(1))
                unit = generic_resistance.group(2).lower().replace("ω", "ohm").replace("Ω", "ohm")
                return number / 1000.0 if unit.startswith("m") else number
        elif spec.key == "storage_capacity_gb" or spec.key == "onboard_storage_gb":
            parsed = _storage_capacity_gb(raw)
            if parsed is not None:
                return parsed
        elif spec.key == "pressure_range_kpa":
            parsed = _pressure_kpa(raw)
            if parsed is not None:
                return parsed
        elif spec.key == "force_range_n":
            parsed = _force_n(raw)
            if parsed is not None:
                return parsed
        elif spec.key == "airflow_range_lpm":
            parsed = _airflow_lpm(raw)
            if parsed is not None:
                return parsed
        elif spec.key == "drive_level_uw":
            parsed = _drive_level_uw(f"drive level {raw}")
            if parsed is not None:
                return parsed
        elif spec.key == "phase_jitter_ps":
            parsed = _phase_jitter_ps(f"jitter {raw}")
            if parsed is not None:
                return parsed

        match = re.search(r"-?[0-9]+(?:[.,][0-9]+)?", raw)
        return _num(match.group(0)) if match else None
    return str(value).strip().lower() if spec.kind == "enum" else str(value).strip()


def compare_engineering_value(spec: EngineeringFieldSpec, actual: Any, expected: Any) -> int:
    """Return 1 match, 0 unknown/unparseable, -1 known mismatch."""
    if actual is None or actual == "" or actual == []:
        return 0
    expected_n = normalize_expected(spec, expected)
    if expected_n is None:
        return 0

    if isinstance(actual, list):
        if spec.comparison in {"exact", "contains"}:
            normalized_actual = [normalize_expected(spec, value) for value in actual]
            return 1 if expected_n in normalized_actual else -1
        # Numeric lists are not treated as exclusive ranges unless the catalog
        # parser established a single value.
        return 0

    actual_n = normalize_expected(spec, actual)
    if actual_n is None:
        return 0

    if spec.kind in {"enum", "text", "bool"}:
        if spec.comparison == "contains":
            return 1 if str(expected_n).lower() in str(actual_n).lower() else -1
        return 1 if actual_n == expected_n else -1

    try:
        a, e = float(actual_n), float(expected_n)
    except (TypeError, ValueError):
        return 0

    if spec.comparison == "min":
        return 1 if a >= e else -1
    if spec.comparison == "max":
        return 1 if a <= e else -1
    if spec.comparison == "covers_min":
        return 1 if a <= e else -1
    if spec.comparison == "covers_max":
        return 1 if a >= e else -1

    scale = max(abs(a), abs(e), 1e-12)
    return 1 if abs(a - e) <= scale * 0.005 else -1


def _format_number(value: float) -> str:
    if math.isclose(value, round(value), rel_tol=0, abs_tol=1e-9):
        return str(int(round(value)))
    return f"{value:.6g}"


def format_engineering_value(spec: EngineeringFieldSpec, value: Any) -> str:
    if value is None:
        return ""
    if spec.kind == "bool":
        return "Yes" if bool(value) else "No"
    if spec.kind == "number":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        if spec.key in {"frequency_hz", "test_frequency_hz", "cutoff_frequency_hz"}:
            if abs(number) >= 1e9:
                return f"{_format_number(number / 1e9)} GHz"
            if abs(number) >= 1e6:
                return f"{_format_number(number / 1e6)} MHz"
            if abs(number) >= 1e3:
                return f"{_format_number(number / 1e3)} kHz"
            return f"{_format_number(number)} Hz"
        return f"{_format_number(number)}{(' ' + spec.unit) if spec.unit else ''}"

    canonical = str(value)
    for label, option_value in spec.choices:
        if canonical.lower() == option_value.lower():
            return label
    return canonical.replace("_", " ").strip().title()


def engineering_reason(spec: EngineeringFieldSpec, expected: Any) -> str:
    label = format_engineering_value(spec, normalize_expected(spec, expected))
    if spec.comparison == "min":
        return f"Engineering: {spec.label} ≥ {label}"
    if spec.comparison == "max":
        return f"Engineering: {spec.label} ≤ {label}"
    if spec.comparison == "covers_min":
        return f"Engineering: {spec.label} ≤ {label}"
    if spec.comparison == "covers_max":
        return f"Engineering: {spec.label} ≥ {label}"
    return f"Engineering: {spec.label}: {label}"


def raw_engineering_from_feature_json(raw_features_json: str | None) -> dict[str, Any]:
    try:
        raw = json.loads(raw_features_json or "{}")
    except Exception:
        return {}
    value = raw.get("engineering")
    return value if isinstance(value, dict) else {}
