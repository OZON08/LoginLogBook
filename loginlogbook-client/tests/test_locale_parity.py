import json
from pathlib import Path

_LOCALES = Path(__file__).parent.parent / "app" / "locales"


def test_en_matches_de_keys():
    de = set(json.loads((_LOCALES / "de.json").read_text(encoding="utf-8")))
    en = set(json.loads((_LOCALES / "en.json").read_text(encoding="utf-8")))
    assert en == de, f"missing={de - en}, extra={en - de}"
