import json
from pathlib import Path

from app.i18n import Translator


def _write(dir: Path, code: str, data: dict) -> None:
    dir.mkdir(parents=True, exist_ok=True)
    (dir / f"{code}.json").write_text(json.dumps(data), encoding="utf-8")


def test_lookup_active_language(tmp_path: Path):
    _write(tmp_path, "de", {"greet": "Hallo"})
    _write(tmp_path, "en", {"greet": "Hello"})
    tr = Translator(tmp_path)
    assert tr.t("greet", "en") == "Hello"


def test_fallback_to_default_then_key(tmp_path: Path):
    _write(tmp_path, "de", {"only_de": "Nur DE"})
    _write(tmp_path, "en", {})
    tr = Translator(tmp_path)
    assert tr.t("only_de", "en") == "Nur DE"      # falls back to de
    assert tr.t("missing", "en") == "missing"     # falls back to key


def test_interpolation(tmp_path: Path):
    _write(tmp_path, "de", {"days": "Letzte {days} Tage"})
    tr = Translator(tmp_path)
    assert tr.t("days", "de", days=7) == "Letzte 7 Tage"


def test_available_from_files(tmp_path: Path):
    _write(tmp_path, "de", {})
    _write(tmp_path, "en", {})
    assert Translator(tmp_path).available() == ["de", "en"]
