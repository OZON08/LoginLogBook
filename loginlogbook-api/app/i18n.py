"""Minimal JSON-backed translation helper with a de -> key fallback chain."""
import json
from pathlib import Path


class Translator:
    def __init__(self, locales_dir: Path, default: str = "de") -> None:
        self._dir = locales_dir
        self._default = default
        self._cache: dict[str, dict] = {}

    def _load(self, code: str) -> dict:
        if code not in self._cache:
            path = self._dir / f"{code}.json"
            if path.exists():
                self._cache[code] = json.loads(path.read_text(encoding="utf-8"))
            else:
                self._cache[code] = {}
        return self._cache[code]

    def t(self, key: str, lang: str, **kwargs) -> str:
        text = self._load(lang).get(key)
        if text is None:
            text = self._load(self._default).get(key, key)
        return text.format(**kwargs) if kwargs else text

    def available(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.json"))
