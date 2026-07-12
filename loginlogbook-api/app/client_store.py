"""JSON-file-backed storage for API client credentials."""
import json
from pathlib import Path


class ClientStore:
    """Stores client name+token pairs as a JSON list on disk."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, records: list[dict]) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(records, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def tokens(self) -> list[str]:
        return [r["token"] for r in self._load()]

    def list_names(self) -> list[str]:
        return [r["name"] for r in self._load()]

    def list_records(self) -> list[dict]:
        return [
            {**r, "allow_free_text": r.get("allow_free_text", True)}
            for r in self._load()
        ]

    def find_by_token(self, token: str) -> dict | None:
        for r in self._load():
            if r["token"] == token:
                return {**r, "allow_free_text": r.get("allow_free_text", True)}
        return None

    def add(self, name: str, token: str) -> None:
        records = self._load()
        if any(r["name"] == name for r in records):
            raise ValueError(f"Client {name!r} already exists")
        records.append({"name": name, "token": token, "allow_free_text": True})
        self._save(records)

    def remove(self, name: str) -> bool:
        records = self._load()
        filtered = [r for r in records if r["name"] != name]
        if len(filtered) == len(records):
            return False
        self._save(filtered)
        return True

    def set_allow_free_text(self, name: str, allow: bool) -> bool:
        records = self._load()
        for r in records:
            if r["name"] == name:
                r["allow_free_text"] = allow
                self._save(records)
                return True
        return False
