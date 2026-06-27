# LoginLogBook Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `loginlogbook-client` PyQt6 fullscreen login overlay that blocks desktop access until a user selects a reason and clicks "Anmelden", with offline caching and BITV 2.0 compliance.

**Architecture:** A single `QMainWindow` covers the full screen. A centered `CardWidget` assembles the two-column UI. Data loads in a background `QThread`; the local cache is checked first so the UI populates instantly. Failed event POSTs go to a file-backed queue retried on reconnect. Platform-specific code (fullscreen lock, key grab, Task Manager disable) is isolated in platform-specific modules imported conditionally.

**Tech Stack:** Python 3.12, PyQt6 ≥ 6.7, httpx ≥ 0.27, pydantic ≥ 2.7, pydantic-settings ≥ 2.3, pytest ≥ 8.2, pytest-qt ≥ 4.4, python-xlib ≥ 0.33 (Linux only), PyInstaller ≥ 6.0 (packaging).

## Global Constraints

- Python version floor: **3.12**.
- All code comments and docstrings in **English**.
- UI language: **German** — all button labels, placeholders, headers, and messages in German.
- Font: `"Segoe UI", system-ui, sans-serif` — no external downloads.
- Minimum font size: **12 px** (BITV 2.0 SC 1.4.4).
- Minimum interactive element height: **44 px** (BITV 2.0 SC 2.5.5).
- Color contrast: all pairs must meet WCAG 2.1 AA as documented in design spec §11.1.
- `QApplication` locale: `de_DE`.
- Every user-facing widget must call `setAccessibleName()` (BITV SC 4.1.2).
- The login flow must **never be blocked** — overlay closes and desktop is released regardless of API success or failure.
- Platform: Windows 10/11 and Linux X11. Wayland forces XWayland via `QT_QPA_PLATFORM=xcb`.
- `CLIENT_TOKEN` from environment: a **unique token per host machine** (one of the entries from `CLIENT_TOKENS` on the API side), sent as `X-Client-Token` header. Never share one token across multiple machines — revoking it would cut off all of them.
- `API_URL` from environment: must be `https://…` in production (nginx TLS termination).
- TLS verification: always enabled. For self-signed internal CA certs, set `API_CA_BUNDLE` env var to the path of the CA certificate file — passed as `httpx.Client(verify=ca_bundle_path)`. Never disable verification entirely (`verify=False` is not an option and is not implemented). Add `api_ca_bundle: Path | None = None` to `Settings`.

---

## File Structure

```
loginlogbook-client/
  pyproject.toml
  loginlogbook-client.desktop          # Linux XDG system-wide autostart
  app/
    __init__.py                        # empty
    config.py                          # Settings (pydantic-settings)
    models.py                          # Reason, EventIn, EventOut, AppConfig
    api_client.py                      # httpx wrapper for all API endpoints
    cache.py                           # File-backed cache: reasons, logo, events, config
    event_queue.py                     # File-backed queue for failed event POSTs
    platform_utils.py                  # Dispatcher: detect OS, call correct platform module
    platform_win32.py                  # Windows: HWND_TOPMOST, DisableTaskMgr
    platform_linux.py                  # Linux X11: XGrabKeyboard, XWayland detection
    ui/
      __init__.py                      # empty
      styles.py                        # Qt stylesheet strings + color token dict
      skeleton.py                      # SkeletonWidget: shimmer placeholder
      search_field.py                  # SearchField: QLineEdit + icon + debounce signal
      reason_list.py                   # ReasonList: filterable QListWidget
      button_row.py                    # ButtonRow: Abmelden + Anmelden buttons
      confirm_dialog.py                # ConfirmDialog: Abmelden confirmation QDialog
      recent_table.py                  # RecentTable: QTableWidget for login history
      footer_bar.py                    # FooterBar: user/host label + status dot
      logo_widget.py                   # LogoWidget: image + skeleton + fallback text
      card_widget.py                   # CardWidget: two-column container
      overlay_window.py                # OverlayWindow: QMainWindow, data loading, wiring
    __main__.py                        # Entry point: QApplication setup, locale, launch
  tests/
    __init__.py                        # empty
    conftest.py                        # fixtures: settings, qtapp
    test_api_client.py
    test_cache.py
    test_event_queue.py
    test_reason_filter.py              # pure logic: no PyQt6
    test_button_states.py              # pytest-qt: button enable/disable
    test_recent_table.py               # pytest-qt: table population
    test_footer_bar.py                 # pytest-qt: status updates
    test_platform_utils.py             # platform detection logic
```

---

### Task 1: Project scaffolding, config, and models

**Files:**
- Create: `loginlogbook-client/pyproject.toml`
- Create: `loginlogbook-client/app/__init__.py` (empty)
- Create: `loginlogbook-client/app/config.py`
- Create: `loginlogbook-client/app/models.py`
- Create: `loginlogbook-client/tests/__init__.py` (empty)
- Create: `loginlogbook-client/tests/conftest.py`
- Create: `loginlogbook-client/tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `app.config.Settings`: `api_url: str`, `client_token: str`, `cache_dir: Path`, `queue_file: Path`.
  - `app.config.get_settings() -> Settings` (cached).
  - `app.models.Reason(id: str, label: str, active: bool = True)`.
  - `app.models.EventIn(event_type, host, os_user, reason, timestamp)`.
  - `app.models.EventOut(event_type, host, os_user, reason, timestamp)`.
  - `app.models.AppConfig(recent_days: int = 7)`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "loginlogbook-client"
version = "0.1.0"
description = "LoginLogBook fullscreen login overlay for Windows and Linux."
requires-python = ">=3.12"
dependencies = [
    "PyQt6>=6.7",
    "httpx>=0.27",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-qt>=4.4",
]
linux = [
    "python-xlib>=0.33",
]
package = [
    "pyinstaller>=6.0",
]

[project.scripts]
loginlogbook-client = "app.__main__:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `app/config.py`**

```python
"""Application settings loaded from environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_url: str = "http://localhost:8000"
    client_token: str = ""
    cache_dir: Path = Path("~/.loginlogbook/cache").expanduser()
    queue_file: Path = Path("~/.loginlogbook/queue.json").expanduser()


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Create `app/models.py`**

```python
"""Data models matching the loginlogbook-api HTTP contract."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EventType = Literal["login", "logout"]


class Reason(BaseModel):
    id: str
    label: str
    active: bool = True


class EventIn(BaseModel):
    event_type: EventType
    host: str
    os_user: str
    reason: str | None = None
    timestamp: datetime


class EventOut(BaseModel):
    event_type: EventType
    host: str
    os_user: str
    reason: str | None = None
    timestamp: datetime


class AppConfig(BaseModel):
    recent_days: int = 7
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
"""Shared test fixtures."""
import pytest

from app.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        api_url="http://testserver",
        client_token="test-token",
        cache_dir=tmp_path / "cache",
        queue_file=tmp_path / "queue.json",
    )
```

- [ ] **Step 5: Write failing test in `tests/test_config.py`**

```python
"""Tests for Settings."""
from pathlib import Path

from app.config import Settings


def test_settings_defaults():
    s = Settings(api_url="http://x", client_token="tok")
    assert s.api_url == "http://x"
    assert isinstance(s.cache_dir, Path)


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("API_URL", "http://custom:8000")
    monkeypatch.setenv("CLIENT_TOKEN", "mytoken")
    s = Settings()
    assert s.api_url == "http://custom:8000"
    assert s.client_token == "mytoken"
```

- [ ] **Step 6: Install and run tests**

```bash
cd loginlogbook-client
pip install -e ".[dev]"
pytest tests/test_config.py -v
```
Expected: both tests PASS.

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-client/
git commit -m "feat(client): scaffold project with config and models"
```

---

### Task 2: API client

**Files:**
- Create: `loginlogbook-client/app/api_client.py`
- Create: `loginlogbook-client/tests/test_api_client.py`

**Interfaces:**
- Consumes: `app.config.Settings`, `app.models.Reason`, `app.models.EventIn`, `app.models.EventOut`, `app.models.AppConfig`.
- Produces:
  - `app.api_client.ApiClient(settings: Settings)` with methods:
    - `get_reasons() -> list[Reason]`
    - `get_logo() -> tuple[bytes, str]` — `(content, content_type)`
    - `get_config() -> AppConfig`
    - `get_recent_events(host: str, days: int) -> list[EventOut]`
    - `post_event(event: EventIn) -> None` — raises `httpx.HTTPError` on failure.

- [ ] **Step 1: Write failing tests in `tests/test_api_client.py`**

```python
"""Tests for the API client using httpx mock transport."""
from datetime import datetime, timezone

import httpx
import pytest

from app.api_client import ApiClient
from app.config import Settings
from app.models import AppConfig, EventIn, EventOut, Reason


def _client(transport: httpx.MockTransport) -> ApiClient:
    s = Settings(api_url="http://api", client_token="tok")
    return ApiClient(s, transport=transport)


def test_get_reasons_returns_list():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200, json=[{"id": "abc", "label": "Wartung", "active": True}]
        )
    )
    reasons = _client(transport).get_reasons()
    assert len(reasons) == 1
    assert reasons[0].label == "Wartung"


def test_get_reasons_sends_client_token():
    captured = {}

    def handler(req):
        captured["token"] = req.headers.get("x-client-token")
        return httpx.Response(200, json=[])

    _client(httpx.MockTransport(handler)).get_reasons()
    assert captured["token"] == "tok"


def test_get_logo_returns_bytes_and_content_type():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200, content=b"PNG", headers={"content-type": "image/png"}
        )
    )
    data, ct = _client(transport).get_logo()
    assert data == b"PNG"
    assert ct == "image/png"


def test_get_config_defaults():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"recent_days": 14})
    )
    cfg = _client(transport).get_config()
    assert cfg.recent_days == 14


def test_get_recent_events():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json=[
                {
                    "event_type": "login",
                    "host": "srv01",
                    "os_user": "alice",
                    "reason": "Wartung",
                    "timestamp": "2026-06-26T08:00:00+00:00",
                }
            ],
        )
    )
    events = _client(transport).get_recent_events("srv01", days=7)
    assert len(events) == 1
    assert events[0].reason == "Wartung"


def test_post_event_raises_on_error():
    transport = httpx.MockTransport(lambda req: httpx.Response(503))
    event = EventIn(
        event_type="login",
        host="srv01",
        os_user="alice",
        reason="Wartung",
        timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(httpx.HTTPStatusError):
        _client(transport).post_event(event)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_api_client.py -v
```
Expected: FAIL with `ModuleNotFoundError: app.api_client`.

- [ ] **Step 3: Create `app/api_client.py`**

```python
"""HTTP client for all loginlogbook-api endpoints."""
import httpx

from app.config import Settings
from app.models import AppConfig, EventIn, EventOut, Reason

_TIMEOUT = 5.0


class ApiClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base = settings.api_url.rstrip("/")
        self._headers = {"X-Client-Token": settings.client_token}
        self._transport = transport
        # Custom CA bundle for self-signed internal certs; None = default system trust store.
        self._verify: str | bool = str(settings.api_ca_bundle) if settings.api_ca_bundle else True

    def _get(self, path: str, **params) -> httpx.Response:
        with httpx.Client(transport=self._transport, verify=self._verify) as c:
            r = c.get(
                f"{self._base}{path}",
                headers=self._headers,
                params=params or None,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            return r

    def get_reasons(self) -> list[Reason]:
        return [Reason(**r) for r in self._get("/reasons").json()]

    def get_logo(self) -> tuple[bytes, str]:
        r = self._get("/branding/logo")
        return r.content, r.headers.get("content-type", "image/png")

    def get_config(self) -> AppConfig:
        return AppConfig(**self._get("/config").json())

    def get_recent_events(self, host: str, days: int) -> list[EventOut]:
        r = self._get("/events/recent", host=host, days=days, limit=100)
        return [EventOut(**e) for e in r.json()]

    def post_event(self, event: EventIn) -> None:
        with httpx.Client(transport=self._transport, verify=self._verify) as c:
            r = c.post(
                f"{self._base}/events",
                headers=self._headers,
                json=event.model_dump(mode="json"),
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_api_client.py -v
```
Expected: all six tests PASS.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-client/app/api_client.py loginlogbook-client/tests/test_api_client.py
git commit -m "feat(client): add API client for all loginlogbook-api endpoints"
```

---

### Task 3: Local cache and event queue

**Files:**
- Create: `loginlogbook-client/app/cache.py`
- Create: `loginlogbook-client/app/event_queue.py`
- Create: `loginlogbook-client/tests/test_cache.py`
- Create: `loginlogbook-client/tests/test_event_queue.py`

**Interfaces:**
- Consumes: `app.models.Reason`, `app.models.EventOut`, `app.models.AppConfig`, `app.models.EventIn`.
- Produces:
  - `app.cache.CacheStore(cache_dir: Path)` with methods:
    - `save_reasons(reasons: list[Reason]) -> None`
    - `load_reasons() -> list[Reason] | None`
    - `save_logo(data: bytes, content_type: str) -> None`
    - `load_logo() -> tuple[bytes, str] | None`
    - `save_recent_events(events: list[EventOut]) -> None`
    - `load_recent_events() -> list[EventOut] | None`
    - `save_config(config: AppConfig) -> None`
    - `load_config() -> AppConfig | None`
  - `app.event_queue.EventQueue(queue_file: Path)` with methods:
    - `enqueue(event: EventIn) -> None`
    - `flush(post_fn: Callable[[EventIn], None]) -> int` — returns number sent.
    - `pending_count() -> int`

- [ ] **Step 1: Write failing tests in `tests/test_cache.py`**

```python
"""Tests for CacheStore."""
from datetime import datetime, timezone
from pathlib import Path

from app.cache import CacheStore
from app.models import AppConfig, EventOut, Reason


def test_reasons_round_trip(tmp_path):
    store = CacheStore(tmp_path)
    reasons = [Reason(id="1", label="Wartung"), Reason(id="2", label="Deployment")]
    store.save_reasons(reasons)
    loaded = store.load_reasons()
    assert loaded is not None
    assert [r.label for r in loaded] == ["Wartung", "Deployment"]


def test_load_reasons_returns_none_when_empty(tmp_path):
    assert CacheStore(tmp_path).load_reasons() is None


def test_logo_round_trip(tmp_path):
    store = CacheStore(tmp_path)
    store.save_logo(b"PNG", "image/png")
    data, ct = store.load_logo()
    assert data == b"PNG"
    assert ct == "image/png"


def test_load_logo_returns_none_when_empty(tmp_path):
    assert CacheStore(tmp_path).load_logo() is None


def test_config_round_trip(tmp_path):
    store = CacheStore(tmp_path)
    store.save_config(AppConfig(recent_days=14))
    cfg = store.load_config()
    assert cfg is not None
    assert cfg.recent_days == 14


def test_recent_events_round_trip(tmp_path):
    store = CacheStore(tmp_path)
    events = [
        EventOut(
            event_type="login",
            host="srv01",
            os_user="alice",
            reason="Wartung",
            timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
        )
    ]
    store.save_recent_events(events)
    loaded = store.load_recent_events()
    assert loaded is not None
    assert loaded[0].reason == "Wartung"
```

- [ ] **Step 2: Write failing tests in `tests/test_event_queue.py`**

```python
"""Tests for EventQueue."""
from datetime import datetime, timezone

import pytest

from app.event_queue import EventQueue
from app.models import EventIn


def _event(user: str = "alice") -> EventIn:
    return EventIn(
        event_type="login",
        host="srv01",
        os_user=user,
        reason="Wartung",
        timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    )


def test_enqueue_increases_count(tmp_path):
    q = EventQueue(tmp_path / "queue.json")
    assert q.pending_count() == 0
    q.enqueue(_event())
    assert q.pending_count() == 1


def test_flush_sends_all_and_clears(tmp_path):
    q = EventQueue(tmp_path / "queue.json")
    q.enqueue(_event("alice"))
    q.enqueue(_event("bob"))
    sent_events = []
    sent = q.flush(lambda e: sent_events.append(e))
    assert sent == 2
    assert q.pending_count() == 0
    assert {e.os_user for e in sent_events} == {"alice", "bob"}


def test_flush_keeps_failed_events(tmp_path):
    q = EventQueue(tmp_path / "queue.json")
    q.enqueue(_event())

    def failing_post(e: EventIn) -> None:
        raise RuntimeError("network down")

    sent = q.flush(failing_post)
    assert sent == 0
    assert q.pending_count() == 1


def test_flush_on_empty_queue_returns_zero(tmp_path):
    q = EventQueue(tmp_path / "queue.json")
    assert q.flush(lambda e: None) == 0
```

- [ ] **Step 3: Create `app/cache.py`**

```python
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
```

- [ ] **Step 4: Create `app/event_queue.py`**

```python
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
```

- [ ] **Step 5: Run all cache and queue tests**

```bash
pytest tests/test_cache.py tests/test_event_queue.py -v
```
Expected: all ten tests PASS.

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-client/app/cache.py loginlogbook-client/app/event_queue.py \
  loginlogbook-client/tests/test_cache.py loginlogbook-client/tests/test_event_queue.py
git commit -m "feat(client): add local cache and file-backed event queue"
```

---

### Task 4: Design tokens, stylesheet, and skeleton widget

**Files:**
- Create: `loginlogbook-client/app/ui/__init__.py` (empty)
- Create: `loginlogbook-client/app/ui/styles.py`
- Create: `loginlogbook-client/app/ui/skeleton.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `app.ui.styles.COLORS: dict[str, str]` — all design-spec color tokens by name.
  - `app.ui.styles.STYLESHEET: str` — full Qt stylesheet applied to `QApplication`.
  - `app.ui.skeleton.SkeletonWidget(parent=None)` — `QWidget` that renders a shimmering gray placeholder. Call `set_geometry_hint(w, h)` to size it.

- [ ] **Step 1: Create `app/ui/styles.py`**

```python
"""Design token colors and Qt stylesheet for the entire overlay."""

COLORS: dict[str, str] = {
    "overlay_bg": "rgba(15, 23, 42, 224)",   # 0.88 * 255 ≈ 224
    "card_bg": "#FFFFFF",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "foreground": "#0F172A",
    "muted": "#475569",
    "border_decorative": "#E2E8F0",
    "border_ui": "#6B7280",
    "selection_bg": "#EFF6FF",
    "selection_border": "#2563EB",
    "destructive": "#DC2626",
    "status_online": "#16A34A",
    "status_offline": "#CA8A04",
    "skeleton": "#E2E8F0",
    "skeleton_shine": "#F8FAFC",
}

STYLESHEET = f"""
QWidget {{
    font-family: "Segoe UI", system-ui, sans-serif;
    color: {COLORS["foreground"]};
}}

QWidget#card {{
    background-color: {COLORS["card_bg"]};
    border-radius: 12px;
}}

QLineEdit#search_field {{
    border: 1px solid {COLORS["border_ui"]};
    border-radius: 6px;
    padding: 8px 8px 8px 36px;
    font-size: 15px;
    background: {COLORS["card_bg"]};
    min-height: 44px;
}}

QLineEdit#search_field:focus {{
    border: 2px solid {COLORS["primary"]};
}}

QListWidget#reason_list {{
    border: none;
    background: {COLORS["card_bg"]};
    outline: none;
}}

QListWidget#reason_list::item {{
    padding: 10px 12px;
    border-left: 3px solid transparent;
    border-bottom: 1px solid {COLORS["border_decorative"]};
    min-height: 38px;
    font-size: 13px;
}}

QListWidget#reason_list::item:selected {{
    background-color: {COLORS["selection_bg"]};
    border-left: 3px solid {COLORS["selection_border"]};
    color: {COLORS["foreground"]};
    font-weight: 500;
}}

QListWidget#reason_list::item:hover:!selected {{
    background-color: #F8FAFC;
}}

QPushButton#btn_anmelden {{
    background-color: {COLORS["primary"]};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    min-height: 44px;
    padding: 0 16px;
}}

QPushButton#btn_anmelden:hover {{
    background-color: {COLORS["primary_hover"]};
}}

QPushButton#btn_anmelden:disabled {{
    background-color: {COLORS["primary"]};
    opacity: 0.38;
    color: #FFFFFF;
}}

QPushButton#btn_abmelden {{
    background-color: transparent;
    color: {COLORS["destructive"]};
    border: 1px solid {COLORS["destructive"]};
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    min-height: 44px;
    padding: 0 16px;
}}

QPushButton#btn_abmelden:hover {{
    background-color: #FEF2F2;
}}

QTableWidget#recent_table {{
    border: none;
    background: {COLORS["card_bg"]};
    gridline-color: {COLORS["border_decorative"]};
    font-size: 13px;
    outline: none;
}}

QTableWidget#recent_table QHeaderView::section {{
    background-color: {COLORS["card_bg"]};
    color: {COLORS["foreground"]};
    font-size: 13px;
    font-weight: 600;
    border-bottom: 1px solid {COLORS["border_ui"]};
    padding: 6px 8px;
}}

QScrollBar:vertical {{
    width: 6px;
    background: transparent;
}}

QScrollBar::handle:vertical {{
    background: {COLORS["border_ui"]};
    border-radius: 3px;
    min-height: 24px;
}}
"""
```

- [ ] **Step 2: Create `app/ui/skeleton.py`**

```python
"""Shimmer skeleton placeholder widget shown while data is loading."""
from PyQt6.QtCore import QPropertyAnimation, QRect, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import QWidget

from app.ui.styles import COLORS


class SkeletonWidget(QWidget):
    """Animated shimmer rectangle used as a loading placeholder."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._shine_pos: float = -1.0
        self._anim = QPropertyAnimation(self, b"shine_pos", self)
        self._anim.setStartValue(-1.0)
        self._anim.setEndValue(2.0)
        self._anim.setDuration(1200)
        self._anim.setLoopCount(-1)
        self._anim.start()
        self.setMinimumHeight(20)

    @pyqtProperty(float)
    def shine_pos(self) -> float:
        return self._shine_pos

    @shine_pos.setter
    def shine_pos(self, value: float) -> None:
        self._shine_pos = value
        self.update()

    def set_geometry_hint(self, width: int, height: int) -> None:
        self.setFixedSize(width, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        grad = QLinearGradient(
            rect.width() * self._shine_pos - rect.width() * 0.3,
            0,
            rect.width() * self._shine_pos + rect.width() * 0.3,
            0,
        )
        grad.setColorAt(0.0, QColor(COLORS["skeleton"]))
        grad.setColorAt(0.5, QColor(COLORS["skeleton_shine"]))
        grad.setColorAt(1.0, QColor(COLORS["skeleton"]))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 6, 6)
```

- [ ] **Step 3: Run a quick import test**

```bash
python -c "from app.ui.styles import STYLESHEET, COLORS; from app.ui.skeleton import SkeletonWidget; print('OK')"
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add loginlogbook-client/app/ui/
git commit -m "feat(client): add design tokens, Qt stylesheet, and skeleton widget"
```

---

### Task 5: Search field and reason list

**Files:**
- Create: `loginlogbook-client/app/ui/search_field.py`
- Create: `loginlogbook-client/app/ui/reason_list.py`
- Create: `loginlogbook-client/tests/test_reason_filter.py`
- Create: `loginlogbook-client/tests/test_button_states.py` (stub only — filled in Task 6)

**Interfaces:**
- Consumes: `app.models.Reason`, `app.ui.styles.COLORS`.
- Produces:
  - `app.ui.search_field.SearchField(parent=None)` — `QWidget`. Emits `filter_changed(str)` signal after 150 ms debounce. `Escape` key clears and emits `filter_changed("")`.
  - `app.ui.reason_list.ReasonList(parent=None)` — `QWidget`. Methods: `populate(reasons: list[Reason]) -> None`, `apply_filter(query: str) -> None`, `selected_reason() -> Reason | None`. Emits `selection_changed(reason_or_none)` where `reason_or_none: Reason | None`. BITV: `setAccessibleName("Anmeldegrund auswählen")`.

- [ ] **Step 1: Write failing tests in `tests/test_reason_filter.py`** (pure logic, no PyQt6)

```python
"""Pure-logic tests for reason filtering — no PyQt6 required."""
from app.models import Reason


def _filter(reasons: list[Reason], query: str) -> list[Reason]:
    """Replicate the filter logic used by ReasonList.apply_filter."""
    q = query.strip().lower()
    if not q:
        return [r for r in reasons if r.active]
    return [r for r in reasons if r.active and q in r.label.lower()]


REASONS = [
    Reason(id="1", label="Wartung"),
    Reason(id="2", label="Deployment"),
    Reason(id="3", label="Incident"),
    Reason(id="4", label="Monitoring"),
    Reason(id="5", label="Wartungsarbeiten", active=False),
]


def test_empty_query_returns_all_active():
    result = _filter(REASONS, "")
    assert len(result) == 4
    assert all(r.active for r in result)


def test_filter_is_case_insensitive():
    result = _filter(REASONS, "WART")
    assert len(result) == 1
    assert result[0].label == "Wartung"


def test_filter_strips_whitespace():
    result = _filter(REASONS, "  deployment  ")
    assert len(result) == 1


def test_filter_excludes_inactive():
    result = _filter(REASONS, "Wartung")
    assert all(r.label != "Wartungsarbeiten" for r in result)


def test_no_match_returns_empty():
    assert _filter(REASONS, "xyzzy") == []
```

- [ ] **Step 2: Run to verify they pass** (pure logic, no implementation needed yet)

```bash
pytest tests/test_reason_filter.py -v
```
Expected: all five tests PASS (logic is self-contained).

- [ ] **Step 3: Create `app/ui/search_field.py`**

```python
"""Search field with debounce and magnifier icon."""
from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from app.ui.styles import COLORS


class SearchField(QWidget):
    filter_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self._emit)

        self._input = QLineEdit(self)
        self._input.setObjectName("search_field")
        self._input.setPlaceholderText("Grund suchen…")
        self._input.textChanged.connect(self._debounce.start)
        self._input.setAccessibleName("Anmeldegrund suchen")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._input)

        # Install key filter for Escape
        self._input.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._input.clear()
                self.filter_changed.emit("")
                return True
        return super().eventFilter(obj, event)

    def _emit(self) -> None:
        self.filter_changed.emit(self._input.text())

    def clear(self) -> None:
        self._input.clear()

    def set_focus(self) -> None:
        self._input.setFocus()
```

- [ ] **Step 4: Create `app/ui/reason_list.py`**

```python
"""Filterable list of login reasons with BITV-compliant selection styling."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.models import Reason


class ReasonList(QWidget):
    selection_changed = pyqtSignal(object)  # emits Reason | None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._reasons: list[Reason] = []
        self._list = QListWidget(self)
        self._list.setObjectName("reason_list")
        self._list.setAccessibleName("Anmeldegrund auswählen")
        self._list.itemSelectionChanged.connect(self._on_selection_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

    def populate(self, reasons: list[Reason]) -> None:
        self._reasons = [r for r in reasons if r.active]
        self._render(self._reasons)

    def apply_filter(self, query: str) -> None:
        q = query.strip().lower()
        filtered = (
            [r for r in self._reasons if q in r.label.lower()]
            if q
            else list(self._reasons)
        )
        self._render(filtered)

    def _render(self, reasons: list[Reason]) -> None:
        self._list.clear()
        for r in reasons:
            item = QListWidgetItem(r.label)
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._list.addItem(item)

    def selected_reason(self) -> Reason | None:
        items = self._list.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.ItemDataRole.UserRole)

    def _on_selection_changed(self) -> None:
        self.selection_changed.emit(self.selected_reason())

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._list.setFocus()
            self._list.keyPressEvent(event)
        else:
            super().keyPressEvent(event)
```

- [ ] **Step 5: Run all tests so far**

```bash
pytest tests/test_reason_filter.py -v
```
Expected: all five PASS (widget tests come in Task 6 with qtbot).

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-client/app/ui/search_field.py \
  loginlogbook-client/app/ui/reason_list.py \
  loginlogbook-client/tests/test_reason_filter.py
git commit -m "feat(client): add search field and reason list"
```

---

### Task 6: Button row and confirm dialog

**Files:**
- Create: `loginlogbook-client/app/ui/button_row.py`
- Create: `loginlogbook-client/app/ui/confirm_dialog.py`
- Create: `loginlogbook-client/tests/test_button_states.py`

**Interfaces:**
- Consumes: `app.models.Reason`.
- Produces:
  - `app.ui.button_row.ButtonRow(parent=None)` — `QWidget`. Methods: `set_selected_reason(reason: Reason | None) -> None`, `set_loading(loading: bool) -> None`. Emits `anmelden_clicked(Reason)` and `abmelden_clicked()`.
  - `app.ui.confirm_dialog.ConfirmDialog(parent=None)` — `QDialog`. Returns `QDialog.DialogCode.Accepted` if user confirms Abmelden.

- [ ] **Step 1: Write failing tests in `tests/test_button_states.py`**

```python
"""Tests for ButtonRow enable/disable and signal emission."""
import pytest
from PyQt6.QtWidgets import QApplication

from app.models import Reason
from app.ui.button_row import ButtonRow


@pytest.fixture
def row(qtbot):
    widget = ButtonRow()
    qtbot.addWidget(widget)
    return widget


def test_anmelden_disabled_initially(row):
    assert not row._btn_anmelden.isEnabled()


def test_anmelden_enabled_after_reason_set(row):
    row.set_selected_reason(Reason(id="1", label="Wartung"))
    assert row._btn_anmelden.isEnabled()


def test_anmelden_disabled_after_reason_cleared(row):
    row.set_selected_reason(Reason(id="1", label="Wartung"))
    row.set_selected_reason(None)
    assert not row._btn_anmelden.isEnabled()


def test_anmelden_emits_signal_with_reason(row, qtbot):
    reason = Reason(id="1", label="Wartung")
    row.set_selected_reason(reason)
    with qtbot.waitSignal(row.anmelden_clicked, timeout=500) as blocker:
        row._btn_anmelden.click()
    assert blocker.args[0].label == "Wartung"


def test_abmelden_emits_signal(row, qtbot):
    with qtbot.waitSignal(row.abmelden_clicked, timeout=500):
        row._btn_abmelden.click()


def test_set_loading_disables_both_buttons(row):
    row.set_selected_reason(Reason(id="1", label="Wartung"))
    row.set_loading(True)
    assert not row._btn_anmelden.isEnabled()
    assert not row._btn_abmelden.isEnabled()
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_button_states.py -v
```
Expected: FAIL with `ModuleNotFoundError: app.ui.button_row`.

- [ ] **Step 3: Create `app/ui/button_row.py`**

```python
"""Abmelden and Anmelden action buttons."""
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget
from PyQt6.QtCore import pyqtSignal

from app.models import Reason


class ButtonRow(QWidget):
    anmelden_clicked = pyqtSignal(Reason)
    abmelden_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._reason: Reason | None = None

        self._btn_abmelden = QPushButton("Abmelden", self)
        self._btn_abmelden.setObjectName("btn_abmelden")
        self._btn_abmelden.setAccessibleName("Abmelden ohne Anmeldungsgrund")
        self._btn_abmelden.clicked.connect(self.abmelden_clicked.emit)

        self._btn_anmelden = QPushButton("Anmelden", self)
        self._btn_anmelden.setObjectName("btn_anmelden")
        self._btn_anmelden.setAccessibleName("Anmelden")
        self._btn_anmelden.setEnabled(False)
        self._btn_anmelden.clicked.connect(self._on_anmelden)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._btn_abmelden)
        layout.addWidget(self._btn_anmelden)

    def set_selected_reason(self, reason: Reason | None) -> None:
        self._reason = reason
        self._btn_anmelden.setEnabled(reason is not None)

    def set_loading(self, loading: bool) -> None:
        self._btn_anmelden.setEnabled(not loading)
        self._btn_abmelden.setEnabled(not loading)
        self._btn_anmelden.setText("…" if loading else "Anmelden")

    def _on_anmelden(self) -> None:
        if self._reason is not None:
            self.anmelden_clicked.emit(self._reason)
```

- [ ] **Step 4: Create `app/ui/confirm_dialog.py`**

```python
"""Abmelden confirmation dialog (BITV SC 2.1.2: documented exit from overlay)."""
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ConfirmDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Abmelden bestätigen")
        self.setAccessibleName("Abmelden bestätigen")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("<b>Wirklich abmelden?</b>", self)
        title.setAccessibleName("Wirklich abmelden?")

        body = QLabel("Es wird kein Anmeldungsgrund erfasst.", self)

        buttons = QDialogButtonBox(self)
        btn_cancel = QPushButton("Abbrechen", self)
        btn_cancel.setDefault(True)
        btn_confirm = QPushButton("Abmelden", self)
        btn_confirm.setObjectName("btn_abmelden")
        btn_confirm.setAccessibleName("Abmelden bestätigen")

        buttons.addButton(btn_cancel, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton(btn_confirm, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(buttons)
```

- [ ] **Step 5: Run button tests**

```bash
pytest tests/test_button_states.py -v
```
Expected: all six tests PASS.

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-client/app/ui/button_row.py \
  loginlogbook-client/app/ui/confirm_dialog.py \
  loginlogbook-client/tests/test_button_states.py
git commit -m "feat(client): add button row and confirm dialog"
```

---

### Task 7: Recent logins table and footer bar

**Files:**
- Create: `loginlogbook-client/app/ui/recent_table.py`
- Create: `loginlogbook-client/app/ui/footer_bar.py`
- Create: `loginlogbook-client/tests/test_recent_table.py`
- Create: `loginlogbook-client/tests/test_footer_bar.py`

**Interfaces:**
- Consumes: `app.models.EventOut`, `app.ui.styles.COLORS`.
- Produces:
  - `app.ui.recent_table.RecentTable(parent=None)` — `QWidget`. Methods: `populate(events: list[EventOut], days: int) -> None`, `set_loading(loading: bool) -> None`. Shows skeleton while loading; shows empty-state label when `events` is empty.
  - `app.ui.footer_bar.FooterBar(parent=None)` — `QWidget`. Methods: `set_user_host(user: str, host: str) -> None`, `set_status(online: bool) -> None`. Status shown as colored dot + text label (BITV: not color-only).

- [ ] **Step 1: Write failing tests in `tests/test_recent_table.py`**

```python
"""Tests for the recent logins table."""
from datetime import datetime, timezone

import pytest

from app.models import EventOut
from app.ui.recent_table import RecentTable


def _event(user: str, reason: str) -> EventOut:
    return EventOut(
        event_type="login",
        host="srv01",
        os_user=user,
        reason=reason,
        timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def table(qtbot):
    w = RecentTable()
    qtbot.addWidget(w)
    return w


def test_populate_sets_row_count(table):
    table.populate([_event("alice", "Wartung"), _event("bob", "Deployment")], days=7)
    assert table._table.rowCount() == 2


def test_populate_shows_username_in_second_column(table):
    table.populate([_event("alice", "Wartung")], days=7)
    assert table._table.item(0, 1).text() == "alice"


def test_populate_shows_reason_in_third_column(table):
    table.populate([_event("alice", "Wartung")], days=7)
    assert table._table.item(0, 2).text() == "Wartung"


def test_empty_events_shows_empty_label(table):
    table.populate([], days=7)
    assert table._empty_label.isVisible()
    assert table._table.rowCount() == 0
```

- [ ] **Step 2: Write failing tests in `tests/test_footer_bar.py`**

```python
"""Tests for the footer bar status indicator."""
import pytest

from app.ui.footer_bar import FooterBar
from app.ui.styles import COLORS


@pytest.fixture
def footer(qtbot):
    w = FooterBar()
    qtbot.addWidget(w)
    return w


def test_set_user_host_updates_label(footer):
    footer.set_user_host("karsten", "SRV01")
    assert "karsten" in footer._user_label.text()
    assert "SRV01" in footer._user_label.text()


def test_online_status_shows_text(footer):
    footer.set_status(online=True)
    assert "Online" in footer._status_label.text()


def test_offline_status_shows_text(footer):
    footer.set_status(online=False)
    assert "Offline" in footer._status_label.text()


def test_status_label_has_accessible_name(footer):
    footer.set_status(online=True)
    assert footer._status_label.accessibleName() != ""
```

- [ ] **Step 3: Create `app/ui/recent_table.py`**

```python
"""Table showing recent login events for this host."""
from datetime import datetime, timezone

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import EventOut
from app.ui.skeleton import SkeletonWidget
from app.ui.styles import COLORS


class RecentTable(QWidget):
    _HEADERS = ["Datum / Uhrzeit", "Benutzer", "Grund"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Letzte Anmeldungen")

        self._header_label = QLabel("Letzte Anmeldungen", self)
        self._header_label.setStyleSheet(
            "font-size: 16px; font-weight: 600;"
        )
        self._days_label = QLabel("", self)
        self._days_label.setStyleSheet(f"font-size: 13px; color: {COLORS['muted']};")

        self._skeleton = SkeletonWidget(self)
        self._skeleton.set_geometry_hint(400, 120)

        self._table = QTableWidget(0, 3, self)
        self._table.setObjectName("recent_table")
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setAccessibleName("Tabelle der letzten Anmeldungen")

        self._empty_label = QLabel("Keine Anmeldungen in diesem Zeitraum", self)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        self._empty_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._header_label)
        layout.addWidget(self._days_label)
        layout.addWidget(self._skeleton)
        layout.addWidget(self._table)
        layout.addWidget(self._empty_label)

        self.set_loading(True)

    def set_loading(self, loading: bool) -> None:
        self._skeleton.setVisible(loading)
        self._table.setVisible(not loading)

    def populate(self, events: list[EventOut], days: int) -> None:
        self._days_label.setText(f"Letzte {days} Tage")
        self._table.setRowCount(0)
        self.set_loading(False)

        if not events:
            self._empty_label.setVisible(True)
            return

        self._empty_label.setVisible(False)
        for event in events:
            row = self._table.rowCount()
            self._table.insertRow(row)
            ts = event.timestamp.astimezone(timezone.utc).strftime("%d.%m. %H:%M")
            for col, text in enumerate([ts, event.os_user, event.reason or ""]):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row, col, item)
```

- [ ] **Step 4: Create `app/ui/footer_bar.py`**

```python
"""Footer bar showing current user/host and API connection status."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui.styles import COLORS


class FooterBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._user_label = QLabel("", self)
        self._user_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['muted']};"
        )
        self._user_label.setAccessibleName("Angemeldeter Benutzer und Hostname")

        self._status_label = QLabel("", self)
        self._status_label.setStyleSheet(f"font-size: 12px; color: {COLORS['muted']};")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(self._user_label)
        layout.addStretch()
        layout.addWidget(self._status_label)

    def set_user_host(self, user: str, host: str) -> None:
        self._user_label.setText(f"{user} · {host}")

    def set_status(self, online: bool) -> None:
        if online:
            dot = f'<span style="color:{COLORS["status_online"]};">●</span>'
            text = f"{dot} Online"
            accessible = "Verbindungsstatus: Online"
        else:
            dot = f'<span style="color:{COLORS["status_offline"]};">●</span>'
            text = f"{dot} Offline – Cache"
            accessible = "Verbindungsstatus: Offline, zwischengespeicherte Daten"
        self._status_label.setText(text)
        self._status_label.setTextFormat(Qt.TextFormat.RichText)
        self._status_label.setAccessibleName(accessible)
```

- [ ] **Step 5: Run table and footer tests**

```bash
pytest tests/test_recent_table.py tests/test_footer_bar.py -v
```
Expected: all eight tests PASS.

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-client/app/ui/recent_table.py \
  loginlogbook-client/app/ui/footer_bar.py \
  loginlogbook-client/tests/test_recent_table.py \
  loginlogbook-client/tests/test_footer_bar.py
git commit -m "feat(client): add recent logins table and footer bar"
```

---

### Task 8: Logo widget and card assembly

**Files:**
- Create: `loginlogbook-client/app/ui/logo_widget.py`
- Create: `loginlogbook-client/app/ui/card_widget.py`

**Interfaces:**
- Consumes: all UI widgets from Tasks 4–7, `app.models.Reason`, `app.models.EventOut`.
- Produces:
  - `app.ui.logo_widget.LogoWidget(parent=None)` — `QWidget`. Methods: `set_logo(data: bytes, content_type: str) -> None`, `set_loading(loading: bool) -> None`. Shows skeleton while loading; falls back to text "LoginLogBook" if `set_logo` is never called and skeleton is hidden.
  - `app.ui.card_widget.CardWidget(parent=None)` — `QWidget`. Assembles all sub-widgets into the two-column card. Public child references: `logo`, `search`, `reason_list`, `button_row`, `recent_table`, `footer`. Applies `--color-card-bg` background and 12 px border-radius via `objectName("card")`.

- [ ] **Step 1: Create `app/ui/logo_widget.py`**

```python
"""Branding logo widget: shows API logo, skeleton while loading, or fallback text."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from app.ui.skeleton import SkeletonWidget


class LogoWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Firmenlogo")
        self.setMaximumHeight(80)

        self._skeleton = SkeletonWidget(self)
        self._skeleton.set_geometry_hint(160, 56)

        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMaximumHeight(72)
        self._image_label.setVisible(False)

        self._fallback_label = QLabel("LoginLogBook", self)
        self._fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fallback_label.setStyleSheet(
            "font-size: 22px; font-weight: 600; color: #0F172A;"
        )
        self._fallback_label.setAccessibleName("LoginLogBook")
        self._fallback_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._skeleton, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._image_label)
        layout.addWidget(self._fallback_label)

    def set_loading(self, loading: bool) -> None:
        self._skeleton.setVisible(loading)
        if not loading and not self._image_label.isVisible():
            self._fallback_label.setVisible(True)

    def set_logo(self, data: bytes, content_type: str) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        scaled = pixmap.scaledToHeight(
            64, Qt.TransformationMode.SmoothTransformation
        )
        self._image_label.setPixmap(scaled)
        self._image_label.setVisible(True)
        self._skeleton.setVisible(False)
        self._fallback_label.setVisible(False)
```

- [ ] **Step 2: Create `app/ui/card_widget.py`**

```python
"""Two-column card widget assembling all overlay sub-widgets."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.button_row import ButtonRow
from app.ui.footer_bar import FooterBar
from app.ui.logo_widget import LogoWidget
from app.ui.reason_list import ReasonList
from app.ui.recent_table import RecentTable
from app.ui.search_field import SearchField
from app.ui.styles import COLORS


class CardWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedWidth(920)

        # --- Sub-widgets (public for overlay wiring) ---
        self.logo = LogoWidget(self)
        self.search = SearchField(self)
        self.reason_list = ReasonList(self)
        self.button_row = ButtonRow(self)
        self.recent_table = RecentTable(self)
        self.footer = FooterBar(self)

        # Left column
        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(self.search)
        left_layout.addWidget(self.reason_list)
        left_layout.addStretch()
        left_layout.addWidget(self.button_row)

        # Vertical divider
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"color: {COLORS['border_ui']};")

        # Right column
        right = QWidget(self)
        right.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.recent_table)

        # Two-column row
        columns = QHBoxLayout()
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(24)
        columns.addWidget(left, 52)
        columns.addWidget(divider)
        columns.addWidget(right, 48)

        # Outer layout: logo + columns + footer
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(24)
        outer.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addLayout(columns)
        outer.addWidget(self.footer)

        self._apply_card_style()

    def _apply_card_style(self) -> None:
        self.setStyleSheet(
            f"QWidget#card {{ background-color: {COLORS['card_bg']};"
            "border-radius: 12px; }}"
        )
        self.setGraphicsEffect(self._make_shadow())

    def _make_shadow(self):
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(64)
        shadow.setOffset(0, 24)
        shadow.setColor(QColor(0, 0, 0, 90))
        return shadow
```

- [ ] **Step 3: Quick smoke test (import only)**

```bash
python -c "from app.ui.card_widget import CardWidget; print('OK')"
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add loginlogbook-client/app/ui/logo_widget.py \
  loginlogbook-client/app/ui/card_widget.py
git commit -m "feat(client): add logo widget and two-column card assembly"
```

---

### Task 9: Overlay window — data loading and full wiring

**Files:**
- Create: `loginlogbook-client/app/ui/overlay_window.py`

**Interfaces:**
- Consumes: `CardWidget`, `ApiClient`, `CacheStore`, `EventQueue`, `app.config.Settings`, all models.
- Produces:
  - `app.ui.overlay_window.OverlayWindow(settings: Settings)` — `QMainWindow`.
    - Shows fullscreen overlay (background `--color-overlay-bg`), card centered.
    - Loads data via `_DataLoader(QThread)` on show; populates from cache first, then updates from API.
    - Handles Anmelden: POSTs event, then closes.
    - Handles Abmelden: shows `ConfirmDialog`, then triggers OS logoff via `platform_utils`.
    - Emits `login_completed()` signal when overlay should close and desktop be released.

- [ ] **Step 1: Create `app/ui/overlay_window.py`**

```python
"""Main fullscreen overlay window — wires all widgets and handles data flow."""
import getpass
import socket
from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QMainWindow, QWidget

from app.api_client import ApiClient
from app.cache import CacheStore
from app.config import Settings
from app.event_queue import EventQueue
from app.models import AppConfig, EventIn, EventOut, Reason
from app.ui.card_widget import CardWidget
from app.ui.confirm_dialog import ConfirmDialog
from app.ui.styles import COLORS, STYLESHEET


class _DataLoader(QThread):
    """Background thread: loads logo, reasons, config, and recent events from API."""

    reasons_loaded = pyqtSignal(list)        # list[Reason]
    logo_loaded = pyqtSignal(bytes, str)     # data, content_type
    config_loaded = pyqtSignal(object)       # AppConfig
    events_loaded = pyqtSignal(list)         # list[EventOut]
    finished_online = pyqtSignal()
    finished_offline = pyqtSignal()

    def __init__(self, client: ApiClient, host: str, days: int) -> None:
        super().__init__()
        self._client = client
        self._host = host
        self._days = days

    def run(self) -> None:
        online = True
        try:
            reasons = self._client.get_reasons()
            self.reasons_loaded.emit(reasons)
        except Exception:
            online = False

        try:
            logo_data, logo_ct = self._client.get_logo()
            self.logo_loaded.emit(logo_data, logo_ct)
        except Exception:
            pass

        try:
            cfg = self._client.get_config()
            self.config_loaded.emit(cfg)
        except Exception:
            pass

        try:
            events = self._client.get_recent_events(self._host, self._days)
            self.events_loaded.emit(events)
        except Exception:
            pass

        if online:
            self.finished_online.emit()
        else:
            self.finished_offline.emit()


class OverlayWindow(QMainWindow):
    login_completed = pyqtSignal()

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._cache = CacheStore(settings.cache_dir)
        self._queue = EventQueue(settings.queue_file)
        self._client = ApiClient(settings)
        self._host = socket.gethostname()
        self._os_user = getpass.getuser()
        self._recent_days = 7
        self._loader: _DataLoader | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(STYLESHEET)

        self._card = CardWidget(self)
        self._card.footer.set_user_host(self._os_user, self._host)

        # Wire signals
        self._card.search.filter_changed.connect(self._card.reason_list.apply_filter)
        self._card.reason_list.selection_changed.connect(
            self._card.button_row.set_selected_reason
        )
        self._card.button_row.anmelden_clicked.connect(self._on_anmelden)
        self._card.button_row.abmelden_clicked.connect(self._on_abmelden)

        # Load from cache immediately
        self._populate_from_cache()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._center_card()
        self._start_loading()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._center_card()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(15, 23, 42, 224))

    def _center_card(self) -> None:
        cw, ch = self._card.width(), self._card.sizeHint().height()
        x = (self.width() - cw) // 2
        y = (self.height() - ch) // 2
        self._card.move(x, max(y, 32))

    def _populate_from_cache(self) -> None:
        if reasons := self._cache.load_reasons():
            self._card.reason_list.populate(reasons)
            self._card.logo.set_loading(False)
        if logo := self._cache.load_logo():
            self._card.logo.set_logo(*logo)
        if cfg := self._cache.load_config():
            self._recent_days = cfg.recent_days
        if events := self._cache.load_recent_events():
            self._card.recent_table.populate(events, self._recent_days)
        self._card.footer.set_status(online=False)
        self._card.search.set_focus()

    def _start_loading(self) -> None:
        self._loader = _DataLoader(self._client, self._host, self._recent_days)
        self._loader.reasons_loaded.connect(self._on_reasons)
        self._loader.logo_loaded.connect(self._on_logo)
        self._loader.config_loaded.connect(self._on_config)
        self._loader.events_loaded.connect(self._on_events)
        self._loader.finished_online.connect(
            lambda: self._card.footer.set_status(online=True)
        )
        self._loader.finished_offline.connect(
            lambda: self._card.footer.set_status(online=False)
        )
        self._loader.start()

    def _on_reasons(self, reasons: list[Reason]) -> None:
        self._card.reason_list.populate(reasons)
        self._cache.save_reasons(reasons)

    def _on_logo(self, data: bytes, content_type: str) -> None:
        self._card.logo.set_logo(data, content_type)
        self._cache.save_logo(data, content_type)

    def _on_config(self, cfg: AppConfig) -> None:
        self._recent_days = cfg.recent_days
        self._cache.save_config(cfg)

    def _on_events(self, events: list[EventOut]) -> None:
        self._card.recent_table.populate(events, self._recent_days)
        self._cache.save_recent_events(events)

    def _on_anmelden(self, reason: Reason) -> None:
        self._card.button_row.set_loading(True)
        event = EventIn(
            event_type="login",
            host=self._host,
            os_user=self._os_user,
            reason=reason.label,
            timestamp=datetime.now(timezone.utc),
        )
        try:
            self._client.post_event(event)
            self._queue.flush(self._client.post_event)
        except Exception:
            self._queue.enqueue(event)
        # Desktop is always released — never block
        self.login_completed.emit()
        self.close()

    def _on_abmelden(self) -> None:
        dialog = ConfirmDialog(self)
        if dialog.exec() == ConfirmDialog.DialogCode.Accepted:
            import app.platform_utils as pu
            pu.logoff()
```

- [ ] **Step 2: Run full test suite**

```bash
pytest -v
```
Expected: all existing tests PASS (no new tests in this task — overlay wiring is covered by smoke test in Task 11).

- [ ] **Step 3: Commit**

```bash
git add loginlogbook-client/app/ui/overlay_window.py
git commit -m "feat(client): add overlay window with data loading and full wiring"
```

---

### Task 10: Platform utilities (Windows + Linux)

**Files:**
- Create: `loginlogbook-client/app/platform_utils.py`
- Create: `loginlogbook-client/app/platform_win32.py`
- Create: `loginlogbook-client/app/platform_linux.py`
- Create: `loginlogbook-client/tests/test_platform_utils.py`

**Interfaces:**
- Consumes: nothing from the rest of the app.
- Produces:
  - `app.platform_utils.setup_fullscreen(window: QMainWindow) -> None` — makes window truly fullscreen (covers taskbar, always on top). Calls the platform-specific implementation.
  - `app.platform_utils.lock_system(window: QMainWindow) -> None` — disables Task Manager (Windows) or grabs keyboard (Linux X11).
  - `app.platform_utils.unlock_system(window: QMainWindow) -> None` — reverses `lock_system`.
  - `app.platform_utils.logoff() -> None` — triggers OS logoff without recording an event.
  - `app.platform_win32.setup_fullscreen(hwnd: int) -> None`
  - `app.platform_win32.lock(hwnd: int) -> None`
  - `app.platform_win32.unlock(hwnd: int) -> None`
  - `app.platform_win32.logoff() -> None`
  - `app.platform_linux.setup_fullscreen(window) -> None`
  - `app.platform_linux.lock(window) -> None`
  - `app.platform_linux.unlock(window) -> None`
  - `app.platform_linux.logoff() -> None`

- [ ] **Step 1: Write failing tests in `tests/test_platform_utils.py`**

```python
"""Tests for platform detection logic."""
import sys

import pytest

import app.platform_utils as pu


def test_detect_returns_win32_or_linux():
    plat = pu._detect_platform()
    assert plat in ("win32", "linux", "other")


def test_detect_matches_sys_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert pu._detect_platform() == "win32"

    monkeypatch.setattr(sys, "platform", "linux")
    assert pu._detect_platform() == "linux"

    monkeypatch.setattr(sys, "platform", "darwin")
    assert pu._detect_platform() == "other"
```

- [ ] **Step 2: Create `app/platform_utils.py`**

```python
"""Platform dispatcher: routes fullscreen, lock, unlock, and logoff to OS-specific impl."""
import sys

from PyQt6.QtWidgets import QMainWindow


def _detect_platform() -> str:
    if sys.platform == "win32":
        return "win32"
    if sys.platform.startswith("linux"):
        return "linux"
    return "other"


def setup_fullscreen(window: QMainWindow) -> None:
    window.showFullScreen()
    if _detect_platform() == "win32":
        import app.platform_win32 as _w32
        hwnd = int(window.winId())
        _w32.setup_fullscreen(hwnd)
    elif _detect_platform() == "linux":
        import app.platform_linux as _lnx
        _lnx.setup_fullscreen(window)


def lock_system(window: QMainWindow) -> None:
    if _detect_platform() == "win32":
        import app.platform_win32 as _w32
        _w32.lock(int(window.winId()))
    elif _detect_platform() == "linux":
        import app.platform_linux as _lnx
        _lnx.lock(window)


def unlock_system(window: QMainWindow) -> None:
    if _detect_platform() == "win32":
        import app.platform_win32 as _w32
        _w32.unlock(int(window.winId()))
    elif _detect_platform() == "linux":
        import app.platform_linux as _lnx
        _lnx.unlock(window)


def logoff() -> None:
    if _detect_platform() == "win32":
        import app.platform_win32 as _w32
        _w32.logoff()
    elif _detect_platform() == "linux":
        import app.platform_linux as _lnx
        _lnx.logoff()
    else:
        raise RuntimeError("logoff not supported on this platform")
```

- [ ] **Step 3: Create `app/platform_win32.py`**

```python
"""Windows-specific: HWND_TOPMOST, DisableTaskMgr, and logoff via ctypes."""
import ctypes
import winreg  # noqa: F401 — Windows only

# SetWindowPos flags
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
_REG_KEY = "DisableTaskMgr"

_set_window_pos = ctypes.windll.user32.SetWindowPos


def setup_fullscreen(hwnd: int) -> None:
    _set_window_pos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
    )


def lock(hwnd: int) -> None:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, _REG_KEY, 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except OSError:
        pass  # Proceed even if registry write fails — overlay still shows


def unlock(hwnd: int) -> None:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, _REG_KEY)
        winreg.CloseKey(key)
    except OSError:
        pass


def logoff() -> None:
    ctypes.windll.user32.ExitWindowsEx(0, 0)  # EWX_LOGOFF = 0
```

- [ ] **Step 4: Create `app/platform_linux.py`**

```python
"""Linux X11-specific: keyboard grab via python-xlib, and logoff via loginctl."""
import os
import subprocess
import sys

from PyQt6.QtWidgets import QMainWindow

_display = None
_grabbed = False


def _get_display():
    global _display
    if _display is None:
        try:
            from Xlib import display as xdisplay
            _display = xdisplay.Display()
        except Exception:
            _display = None
    return _display


def setup_fullscreen(window: QMainWindow) -> None:
    # Force XWayland if Wayland is detected
    if os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    # Qt showFullScreen already covers the taskbar under XWayland / X11
    # No additional steps needed for window positioning on Linux


def lock(window: QMainWindow) -> None:
    global _grabbed
    d = _get_display()
    if d is None:
        return
    try:
        from Xlib import X
        root = d.screen().root
        root.grab_keyboard(
            True,                    # owner_events
            X.GrabModeAsync,         # pointer_mode
            X.GrabModeAsync,         # keyboard_mode
            X.CurrentTime,
        )
        d.flush()
        _grabbed = True
    except Exception:
        pass


def unlock(window: QMainWindow) -> None:
    global _grabbed
    if not _grabbed:
        return
    d = _get_display()
    if d is None:
        return
    try:
        from Xlib import X
        d.ungrab_keyboard(X.CurrentTime)
        d.flush()
        _grabbed = False
    except Exception:
        pass


def logoff() -> None:
    # Try loginctl first (systemd), fall back to pkill session
    try:
        subprocess.run(["loginctl", "terminate-session", ""], check=False)
    except FileNotFoundError:
        subprocess.run(["pkill", "-KILL", "-u", os.getlogin()], check=False)
```

- [ ] **Step 5: Run platform detection tests**

```bash
pytest tests/test_platform_utils.py -v
```
Expected: all three tests PASS.

- [ ] **Step 6: Integrate lock/unlock into OverlayWindow**

In `app/ui/overlay_window.py`, add to `showEvent`:

```python
def showEvent(self, event) -> None:
    super().showEvent(event)
    self._center_card()
    import app.platform_utils as pu
    pu.setup_fullscreen(self)
    pu.lock_system(self)
    self._start_loading()
```

And add to `closeEvent`:

```python
def closeEvent(self, event) -> None:
    import app.platform_utils as pu
    pu.unlock_system(self)
    super().closeEvent(event)
```

- [ ] **Step 7: Run full test suite**

```bash
pytest -v
```
Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add loginlogbook-client/app/platform_utils.py \
  loginlogbook-client/app/platform_win32.py \
  loginlogbook-client/app/platform_linux.py \
  loginlogbook-client/app/ui/overlay_window.py \
  loginlogbook-client/tests/test_platform_utils.py
git commit -m "feat(client): add platform utilities for Windows and Linux X11"
```

---

### Task 11: Entry point, autostart, and packaging

**Files:**
- Create: `loginlogbook-client/app/__main__.py`
- Create: `loginlogbook-client/loginlogbook-client.desktop`
- Create: `loginlogbook-client/build.spec` (PyInstaller spec)

**Interfaces:**
- Consumes: `OverlayWindow`, `Settings`, `get_settings`, `app.ui.styles.STYLESHEET`.
- Produces: `main()` entry point; `loginlogbook-client` CLI command; distributable binary via PyInstaller.

- [ ] **Step 1: Create `app/__main__.py`**

```python
"""Application entry point."""
import sys

from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtWidgets import QApplication

from app.config import get_settings
from app.ui.overlay_window import OverlayWindow
from app.ui.styles import STYLESHEET


def main() -> None:
    # Force XWayland before QApplication is created
    import os
    if os.environ.get("WAYLAND_DISPLAY") and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    app.setLocale(QLocale(QLocale.Language.German, QLocale.Country.Germany))
    app.setApplicationName("LoginLogBook")
    app.setStyleSheet(STYLESHEET)

    settings = get_settings()
    window = OverlayWindow(settings)
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `loginlogbook-client.desktop`**

```ini
[Desktop Entry]
Type=Application
Name=LoginLogBook
Exec=/usr/local/bin/loginlogbook-client
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=LoginLogBook login reason overlay
```

Install system-wide: copy to `/etc/xdg/autostart/loginlogbook-client.desktop`.

- [ ] **Step 3: Create `build.spec` for PyInstaller**

```python
# PyInstaller spec for loginlogbook-client
# Build with: pyinstaller build.spec
block_cipher = None

a = Analysis(
    ["app/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=["PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets"],
    hookspath=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="loginlogbook-client",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)
```

- [ ] **Step 4: Smoke test — launch and immediately close**

```bash
python -c "
import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from app.config import Settings
from app.ui.overlay_window import OverlayWindow
app = QApplication(sys.argv)
s = Settings(api_url='http://localhost:9999', client_token='x')
w = OverlayWindow(s)
w.show()
QTimer.singleShot(500, app.quit)
sys.exit(app.exec())
"
```
Expected: overlay opens briefly, then closes without errors.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```
Expected: all tests PASS.

- [ ] **Step 6: Build binary (optional, for deployment verification)**

```bash
pip install -e ".[package]"
pyinstaller build.spec
./dist/loginlogbook-client --help 2>/dev/null || echo "binary OK"
```

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-client/app/__main__.py \
  loginlogbook-client/loginlogbook-client.desktop \
  loginlogbook-client/build.spec
git commit -m "feat(client): add entry point, Linux autostart desktop file, and PyInstaller spec"
```

---

## Definition of Done (Client)

- `pytest -v` passes; all unit and widget tests green.
- Overlay opens fullscreen (covers taskbar) on Windows and Linux X11.
- Reason list filters live as user types; Anmelden activates only after selection.
- Login event POSTed on Anmelden; queued locally if API unreachable.
- Desktop released regardless of API success or failure.
- Abmelden triggers confirmation dialog, then OS logoff with no event recorded.
- Status dot + text label shows Online / Offline (not color-only — BITV 1.4.1).
- All interactive elements have `setAccessibleName()` set.
- `QApplication` locale is `de_DE`.
- PyInstaller binary produced and tested on target OS.

This client consumes the API contract from `loginlogbook-api`. The two new API endpoints required before full client testing: `GET /config` and the `days` parameter on `GET /events/recent` (see design spec §9).
