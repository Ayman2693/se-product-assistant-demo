from app.services.matcher import (
    _antenna_connectors,
    _antenna_count,
    _bluetooth_version,
    _footprint_mm2,
    _gnss_dual_band,
    _host_interfaces,
)

def test_jody_interfaces_and_antennas():
    h = "u-blox host-based wi-fi 6 pcie/sdio 3 ant.pins bt/ble 5.3"
    assert _host_interfaces(h) == {"pcie", "sdio"}
    assert _antenna_connectors(h) == {"antenna_pin"}
    assert _antenna_count(h) == 3
    assert _bluetooth_version(h) == 5.3

def test_maya_ufl_and_size():
    h = "wi-fi 6 + ble5.3 2x u.fl connect. 10.4x14.3x1.9mm"
    assert _antenna_connectors(h) == {"ufl"}
    assert _antenna_count(h) == 2
    assert _bluetooth_version(h) == 5.3
    assert abs(_footprint_mm2(h) - 148.72) < 0.01

def test_gnss_l1_l5():
    assert _gnss_dual_band("gnss (l1+l5)") is True
    assert _gnss_dual_band("gnss (l1)") is False
