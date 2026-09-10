import json
from types import SimpleNamespace

from app.services.feature_extractor import extract_features
from app.services.matcher import _product_role

def test_ble53_is_detected():
    x = extract_features(
        "MAYA-W266-00B",
        "u-blox",
        "Wi-Fi",
        "u-blox*Host-based Multiradio Module*Wi-Fi 6+BLE5.3 PCB ant. / ant. pin*10.4x14.3x1.9mm*NXP IW611",
        [],
    )
    assert "bluetooth" in x["technologies"]
    assert x["has_bluetooth"] is True

def test_dual_antenna_capability_is_both():
    x = extract_features(
        "MAYA-W266-00B",
        "u-blox",
        "Wi-Fi",
        "Wi-Fi 6+BLE5.3 PCB ant. / ant. pin",
        [],
    )
    assert x["antenna"] == "both"

def test_evk_role():
    p = SimpleNamespace(
        category="Short Range Evaluation",
        part_number="EVK-JODY-W377-00A",
        description="Evaluation kit for JODY-W377"
    )
    assert _product_role(p) == "evaluation"

def test_external_antenna_role():
    p = SimpleNamespace(
        category="External Antennas",
        part_number="SZW-N-1W13",
        description="External WiFi antenna"
    )
    assert _product_role(p) == "antenna"

def test_module_role():
    p = SimpleNamespace(
        category="Wi-Fi",
        part_number="MAYA-W260-00B",
        description="Host-based Multiradio Module"
    )
    assert _product_role(p) == "primary"
