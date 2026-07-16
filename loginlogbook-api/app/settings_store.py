"""File-backed storage for global application settings (language, ...)."""
import json
from pathlib import Path

_DEFAULTS: dict = {"language": "de"}


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if not self._path.exists():
            return dict(_DEFAULTS)
        return {**_DEFAULTS, **json.loads(self._path.read_text(encoding="utf-8"))}

    def save(self, data: dict) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self._path)
