"""Client-side translation helper with active -> de -> key fallback."""
import json
from pathlib import Path

_LOCALES = Path(__file__).parent / "locales"
_DEFAULT = "de"


class Translator:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self._active = _DEFAULT

    def _load(self, code: str) -> dict:
        if code not in self._cache:
            path = _LOCALES / f"{code}.json"
            self._cache[code] = (
                json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            )
        return self._cache[code]

    def set_language(self, code: str) -> None:
        self._active = code

    def t(self, key: str, **kwargs) -> str:
        text = self._load(self._active).get(key)
        if text is None:
            text = self._load(_DEFAULT).get(key, key)
        return text.format(**kwargs) if kwargs else text

    def available(self) -> list[str]:
        return sorted(p.stem for p in _LOCALES.glob("*.json"))


_translator = Translator()
set_language = _translator.set_language
t = _translator.t
available = _translator.available
