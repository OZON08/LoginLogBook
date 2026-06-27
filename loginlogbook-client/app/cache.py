"""File-backed local cache for reasons, logo, recent events, and config."""
import json
from pathlib import Path

from app.models import AppConfig, EventOut, Reason


class CacheStore:
    def __init__(self, cache_dir: Path) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save_reasons(self, reasons: list[Reason]) -> None:
        (self._dir / "reasons.json").write_text(
            json.dumps([r.model_dump() for r in reasons]), encoding="utf-8"
        )

    def load_reasons(self) -> list[Reason] | None:
        p = self._dir / "reasons.json"
        if not p.exists():
            return None
        return [Reason(**r) for r in json.loads(p.read_text(encoding="utf-8"))]

    def save_logo(self, data: bytes, content_type: str) -> None:
        (self._dir / "logo.bin").write_bytes(data)
        (self._dir / "logo_meta.json").write_text(
            json.dumps({"content_type": content_type}), encoding="utf-8"
        )

    def load_logo(self) -> tuple[bytes, str] | None:
        p, m = self._dir / "logo.bin", self._dir / "logo_meta.json"
        if not p.exists() or not m.exists():
            return None
        meta = json.loads(m.read_text(encoding="utf-8"))
        return p.read_bytes(), meta["content_type"]

    def save_recent_events(self, events: list[EventOut]) -> None:
        (self._dir / "recent_events.json").write_text(
            json.dumps([e.model_dump(mode="json") for e in events]), encoding="utf-8"
        )

    def load_recent_events(self) -> list[EventOut] | None:
        p = self._dir / "recent_events.json"
        if not p.exists():
            return None
        return [EventOut(**e) for e in json.loads(p.read_text(encoding="utf-8"))]

    def save_config(self, config: AppConfig) -> None:
        (self._dir / "config.json").write_text(
            json.dumps(config.model_dump()), encoding="utf-8"
        )

    def load_config(self) -> AppConfig | None:
        p = self._dir / "config.json"
        if not p.exists():
            return None
        return AppConfig(**json.loads(p.read_text(encoding="utf-8")))
