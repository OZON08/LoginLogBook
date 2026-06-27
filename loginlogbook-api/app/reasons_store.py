"""JSON-file-backed persistence for login reasons."""
import json
import uuid
from pathlib import Path

from app.models import Reason


class ReasonsStore:
    """Stores reasons as a JSON list on disk. Not safe for concurrent writers."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[Reason]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return [Reason(**item) for item in raw]

    def _save(self, reasons: list[Reason]) -> None:
        data = [r.model_dump() for r in reasons]
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_active(self) -> list[Reason]:
        """Return all reasons that are still active."""
        return [r for r in self._load() if r.active]

    def add(self, label: str) -> Reason:
        """Create a new active reason and persist it."""
        reasons = self._load()
        reason = Reason(id=uuid.uuid4().hex, label=label, active=True)
        reasons.append(reason)
        self._save(reasons)
        return reason

    def deactivate(self, reason_id: str) -> bool:
        """Mark a reason inactive. Returns False if the id is unknown."""
        reasons = self._load()
        found = False
        for reason in reasons:
            if reason.id == reason_id:
                reason.active = False
                found = True
        if found:
            self._save(reasons)
        return found
