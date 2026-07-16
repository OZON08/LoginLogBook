from pathlib import Path

from app.settings_store import SettingsStore


def test_load_returns_default_when_missing(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    assert store.load() == {"language": "de"}


def test_save_then_load_roundtrip(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    store.save({"language": "en"})
    assert store.load() == {"language": "en"}


def test_load_merges_defaults(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text("{}", encoding="utf-8")
    assert SettingsStore(path).load() == {"language": "de"}
