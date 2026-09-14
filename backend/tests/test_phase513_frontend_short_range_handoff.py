from pathlib import Path
APP = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")


def test_multiradio_is_first_short_range_shortcut():
    first = APP.index('label: "Multiradio (Wi-Fi + Bluetooth)"')
    cellular = APP.index('label: "Cellular"', first)
    assert first < cellular
    assert 'label: "Evaluation / development kits"' in APP
    assert 'label: "Other RF components"' in APP


def test_bluetooth_modes_multiselect_maps_classic_to_combined_category():
    assert 'key: "bluetoothModes"' in APP
    assert 'Bluetooth Low Energy (LE)' in APP
    assert 'Bluetooth Classic (BR/EDR)' in APP
    assert 'next.catalogCategory="Bluetooth Classic + LE"' in APP or 'next.catalogCategory = "Bluetooth Classic + LE"' in APP
    assert 'key === "bluetoothModes"' in APP


def test_suggested_email_removed_and_contact_fae_remains():
    assert "Suggested email to SE" not in APP
    assert "Open email draft" not in APP
    assert "commercialEmailDraft" not in APP
    assert "technicalEmailDraft" not in APP
    assert "Contact FAE" in APP
    assert "support@spezial.com" in APP


def test_open_option_present():
    assert "Not determined / open" in APP
