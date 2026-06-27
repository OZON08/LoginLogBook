"""File-backed queue for event POSTs that failed due to API unavailability."""
import json
from collections.abc import Callable
from pathlib import Path

from app.models import EventIn


class EventQueue:
    def __init__(self, queue_file: Path) -> None:
        self._path = queue_file
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def enqueue(self, event: EventIn) -> None:
        events = self._load()
        events.append(event.model_dump(mode="json"))
        self._save(events)

    def flush(self, post_fn: Callable[[EventIn], None]) -> int:
        """Attempt to POST all queued events. Returns the number successfully sent."""
        events = self._load()
        if not events:
            return 0
        remaining, sent = [], 0
        for raw in events:
            try:
                post_fn(EventIn(**raw))
                sent += 1
            except Exception:
                remaining.append(raw)
        self._save(remaining)
        return sent

    def pending_count(self) -> int:
        return len(self._load())

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, events: list[dict]) -> None:
        self._path.write_text(json.dumps(events), encoding="utf-8")
