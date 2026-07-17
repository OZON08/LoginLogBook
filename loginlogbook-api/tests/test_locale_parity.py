import json
from pathlib import Path

import pytest

_APP = Path(__file__).parent.parent / "app"
_DIRS = [_APP / "locales" / "api",
         _APP / "locales" / "admin",
         _APP / "locales" / "grafana"]


@pytest.mark.parametrize("locale_dir", _DIRS, ids=lambda p: p.name)
def test_every_language_has_same_keys_as_de(locale_dir: Path):
    de = set(json.loads((locale_dir / "de.json").read_text(encoding="utf-8")))
    for other in locale_dir.glob("*.json"):
        if other.name == "de.json":
            continue
        keys = set(json.loads(other.read_text(encoding="utf-8")))
        assert keys == de, f"{other} differs from de.json: " \
                           f"missing={de - keys}, extra={keys - de}"
