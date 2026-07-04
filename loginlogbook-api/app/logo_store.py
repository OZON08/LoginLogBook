"""File-backed storage for the central branding logo."""
import json
from pathlib import Path


class LogoStore:
    """Persists a single branding logo plus its media type on disk."""

    ALLOWED = {"image/png": "logo.png", "image/svg+xml": "logo.svg"}

    def __init__(self, logo_dir: Path, max_bytes: int) -> None:
        self._dir = logo_dir
        self._max_bytes = max_bytes
        self._dir.mkdir(parents=True, exist_ok=True)
        self._meta = self._dir / "meta.json"

    def save(self, content: bytes, content_type: str) -> None:
        """Validate and store the logo. Raises ValueError on invalid input."""
        if content_type not in self.ALLOWED:
            raise ValueError(f"Unsupported content type: {content_type}")
        if len(content) > self._max_bytes:
            raise ValueError("Logo exceeds maximum size")
        filename = self.ALLOWED[content_type]
        (self._dir / filename).write_bytes(content)
        self._meta.write_text(
            json.dumps({"filename": filename, "content_type": content_type}),
            encoding="utf-8",
        )

    def load(self) -> tuple[bytes, str] | None:
        """Return (content, content_type) or None if no logo exists."""
        if not self._meta.exists():
            return None
        meta = json.loads(self._meta.read_text(encoding="utf-8"))
        path = self._dir / meta["filename"]
        if not path.exists():
            return None
        return path.read_bytes(), meta["content_type"]
