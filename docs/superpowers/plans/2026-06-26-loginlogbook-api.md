# LoginLogBook API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the central `loginlogbook-api` FastAPI backend that manages login reasons, distributes a branding logo, ingests login/logout events into InfluxDB, and serves recent logins.

**Architecture:** A FastAPI application is the only component with InfluxDB access. Reasons are persisted in a JSON file, the branding logo as a file on a mounted volume, and events in an InfluxDB `login_events` measurement. The app, reasons store, logo store, and InfluxDB wrapper are separate modules with narrow interfaces so each can be tested in isolation. Routers are thin and delegate to these modules.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, pydantic / pydantic-settings, influxdb-client, pytest, httpx (TestClient), Docker + docker-compose, InfluxDB 2.x.

## Global Constraints

- Python version floor: **3.12**.
- All code comments and docstrings in **English**.
- InfluxDB is reachable **only** from the API — never expose its token to clients.
- Two API tokens, supplied via environment: `ADMIN_TOKEN` (admin endpoints) and `CLIENT_TOKEN` (client read/write endpoints).
- Admin endpoints require header `X-Admin-Token`; client endpoints require header `X-Client-Token`.
- Event timestamps are stored in **UTC**.
- InfluxDB measurement name: `login_events`. Tags: `host`, `os_user`, `event_type` (`login`|`logout`), `reason` (login only). Field: `count` = 1.
- Logo: accepted formats **PNG and SVG**, max size **2 MB** (2_097_152 bytes).
- The login flow must never be blocked by API failures — this is enforced on the client side, but the API must return correct status codes (503 when InfluxDB is unreachable) so the client can react.

---

## File Structure

```
loginlogbook-api/
  pyproject.toml              # project metadata + dependencies
  Dockerfile                  # API container image
  docker-compose.yml          # api + influxdb services
  .env.example                # documented environment variables
  app/
    __init__.py
    config.py                 # Settings loaded from environment
    models.py                 # Pydantic request/response models
    auth.py                   # admin/client token dependencies
    reasons_store.py          # JSON-file-backed reasons persistence
    logo_store.py             # file-backed logo persistence
    influx.py                 # InfluxDB wrapper: write event, query recent, ping
    main.py                   # FastAPI app, wiring, dependency providers
    routers/
      __init__.py
      health.py               # GET /health
      reasons.py              # GET/POST/DELETE /reasons
      events.py               # POST /events, GET /events/recent
      branding.py             # GET/PUT /branding/logo
  tests/
    __init__.py
    conftest.py               # fixtures: test client, temp stores, fake influx
    test_health.py
    test_reasons.py
    test_events.py
    test_branding.py
    test_integration_influx.py  # runs only when an InfluxDB container is available
```

Each `app/*.py` module has one responsibility. Routers are thin; persistence
and InfluxDB access live in dedicated modules so they can be tested without
the web layer.

---

### Task 1: Project scaffolding, config, and health liveness endpoint

**Files:**
- Create: `loginlogbook-api/pyproject.toml`
- Create: `loginlogbook-api/app/__init__.py` (empty)
- Create: `loginlogbook-api/app/config.py`
- Create: `loginlogbook-api/app/main.py`
- Create: `loginlogbook-api/app/routers/__init__.py` (empty)
- Create: `loginlogbook-api/app/routers/health.py`
- Create: `loginlogbook-api/tests/__init__.py` (empty)
- Create: `loginlogbook-api/tests/conftest.py`
- Create: `loginlogbook-api/tests/test_health.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `app.config.Settings` (pydantic-settings) with fields: `influx_url: str`, `influx_token: str`, `influx_org: str`, `influx_bucket: str`, `admin_token: str`, `client_token: str`, `reasons_file: Path`, `logo_dir: Path`, `logo_max_bytes: int = 2_097_152`.
  - `app.config.get_settings() -> Settings` (cached).
  - `app.main.create_app() -> FastAPI` factory.
  - `GET /health` returning `{"status": "ok"}` with HTTP 200 (liveness only; InfluxDB readiness added in Task 7).

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "loginlogbook-api"
version = "0.1.0"
description = "Central backend for LoginLogBook: reasons, logo, and login/logout events."
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "influxdb-client>=1.43",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "httpx>=0.27",
]

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
    """Runtime configuration. Values come from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    influx_url: str = "http://influxdb:8086"
    influx_token: str = ""
    influx_org: str = "loginlogbook"
    influx_bucket: str = "logins"

    admin_token: str = ""
    client_token: str = ""

    reasons_file: Path = Path("/data/reasons.json")
    logo_dir: Path = Path("/data/logo")
    logo_max_bytes: int = 2_097_152


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
```

- [ ] **Step 3: Create `app/routers/health.py`**

```python
"""Health endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. InfluxDB readiness is added in a later task."""
    return {"status": "ok"}
```

- [ ] **Step 4: Create `app/main.py`**

```python
"""FastAPI application factory and wiring."""
from fastapi import FastAPI

from app.routers import health


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 5: Create `tests/conftest.py`**

```python
"""Shared test fixtures."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """A TestClient bound to a fresh app instance."""
    return TestClient(create_app())
```

- [ ] **Step 6: Write the failing test in `tests/test_health.py`**

```python
"""Tests for the health endpoint."""


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 7: Run the test to verify it passes**

Run (from `loginlogbook-api/`):
```bash
pip install -e ".[dev]"
pytest tests/test_health.py -v
```
Expected: `test_health_returns_ok PASSED`.

- [ ] **Step 8: Commit**

```bash
git add loginlogbook-api/pyproject.toml loginlogbook-api/app loginlogbook-api/tests
git commit -m "feat(api): scaffold FastAPI app with config and health endpoint"
```

---

### Task 2: Token authentication dependencies

**Files:**
- Create: `loginlogbook-api/app/auth.py`
- Create: `loginlogbook-api/tests/test_auth.py`

**Interfaces:**
- Consumes: `app.config.get_settings`, `Settings.admin_token`, `Settings.client_token`.
- Produces:
  - `app.auth.require_admin(x_admin_token: str = Header(...)) -> None` — raises `HTTPException(401)` if the header is missing or does not match `Settings.admin_token`.
  - `app.auth.require_client(x_client_token: str = Header(...)) -> None` — same for `Settings.client_token`.
  These are FastAPI dependencies to be attached to routers in later tasks.

- [ ] **Step 1: Write the failing test in `tests/test_auth.py`**

```python
"""Tests for token authentication dependencies."""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import auth
from app.config import Settings, get_settings


def _app_with_protected_routes() -> FastAPI:
    app = FastAPI()

    @app.get("/admin-only", dependencies=[Depends(auth.require_admin)])
    def admin_only() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/client-only", dependencies=[Depends(auth.require_client)])
    def client_only() -> dict[str, bool]:
        return {"ok": True}

    app.dependency_overrides[get_settings] = lambda: Settings(
        admin_token="admin-secret", client_token="client-secret"
    )
    return app


def test_admin_route_rejects_missing_token():
    client = TestClient(_app_with_protected_routes())
    assert client.get("/admin-only").status_code == 401


def test_admin_route_rejects_wrong_token():
    client = TestClient(_app_with_protected_routes())
    resp = client.get("/admin-only", headers={"X-Admin-Token": "nope"})
    assert resp.status_code == 401


def test_admin_route_accepts_correct_token():
    client = TestClient(_app_with_protected_routes())
    resp = client.get("/admin-only", headers={"X-Admin-Token": "admin-secret"})
    assert resp.status_code == 200


def test_client_route_accepts_correct_token():
    client = TestClient(_app_with_protected_routes())
    resp = client.get("/client-only", headers={"X-Client-Token": "client-secret"})
    assert resp.status_code == 200
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL with `ImportError` / `AttributeError` on `auth.require_admin`.

- [ ] **Step 3: Create `app/auth.py`**

```python
"""Token-based authentication dependencies."""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    """Allow the request only if the admin token header matches."""
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token"
        )


def require_client(
    settings: Annotated[Settings, Depends(get_settings)],
    x_client_token: Annotated[str | None, Header()] = None,
) -> None:
    """Allow the request only if the client token header matches."""
    if not x_client_token or x_client_token != settings.client_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client token"
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_auth.py -v`
Expected: all four tests PASS.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-api/app/auth.py loginlogbook-api/tests/test_auth.py
git commit -m "feat(api): add admin and client token dependencies"
```

---

### Task 3: Reasons store and reasons router

**Files:**
- Create: `loginlogbook-api/app/models.py`
- Create: `loginlogbook-api/app/reasons_store.py`
- Create: `loginlogbook-api/app/routers/reasons.py`
- Modify: `loginlogbook-api/app/main.py`
- Modify: `loginlogbook-api/tests/conftest.py`
- Create: `loginlogbook-api/tests/test_reasons.py`

**Interfaces:**
- Consumes: `app.auth.require_admin`, `app.auth.require_client`, `app.config.get_settings`.
- Produces:
  - `app.models.Reason` (BaseModel): `id: str`, `label: str`, `active: bool = True`.
  - `app.models.ReasonIn` (BaseModel): `label: str`.
  - `app.reasons_store.ReasonsStore(path: Path)` with methods:
    - `list_active() -> list[Reason]`
    - `add(label: str) -> Reason` (generates a uuid4 hex `id`)
    - `deactivate(reason_id: str) -> bool` (returns False if not found)
  - `app.main.get_reasons_store() -> ReasonsStore` dependency provider (reads `Settings.reasons_file`).
  - Router endpoints: `GET /reasons` (client token), `POST /reasons` (admin token), `DELETE /reasons/{reason_id}` (admin token).

- [ ] **Step 1: Create `app/models.py`**

```python
"""Pydantic request and response models."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EventType = Literal["login", "logout"]


class ReasonIn(BaseModel):
    """Payload for creating a reason."""

    label: str


class Reason(BaseModel):
    """A selectable login reason."""

    id: str
    label: str
    active: bool = True


class EventIn(BaseModel):
    """Payload for recording a login/logout event."""

    event_type: EventType
    host: str
    os_user: str
    reason: str | None = None
    timestamp: datetime


class EventOut(BaseModel):
    """A recorded event returned by recent-event queries."""

    event_type: EventType
    host: str
    os_user: str
    reason: str | None = None
    timestamp: datetime
```

- [ ] **Step 2: Write the failing test in `tests/test_reasons.py`**

```python
"""Tests for the reasons store and reasons endpoints."""
from pathlib import Path

from app.reasons_store import ReasonsStore


def test_store_add_and_list(tmp_path: Path):
    store = ReasonsStore(tmp_path / "reasons.json")
    created = store.add("Maintenance")
    assert created.label == "Maintenance"
    assert created.active is True
    assert [r.label for r in store.list_active()] == ["Maintenance"]


def test_store_deactivate_hides_reason(tmp_path: Path):
    store = ReasonsStore(tmp_path / "reasons.json")
    created = store.add("Incident")
    assert store.deactivate(created.id) is True
    assert store.list_active() == []


def test_store_deactivate_unknown_returns_false(tmp_path: Path):
    store = ReasonsStore(tmp_path / "reasons.json")
    assert store.deactivate("does-not-exist") is False


def test_store_persists_across_instances(tmp_path: Path):
    path = tmp_path / "reasons.json"
    ReasonsStore(path).add("Deployment")
    reopened = ReasonsStore(path)
    assert [r.label for r in reopened.list_active()] == ["Deployment"]
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/test_reasons.py -v`
Expected: FAIL with `ModuleNotFoundError: app.reasons_store`.

- [ ] **Step 4: Create `app/reasons_store.py`**

```python
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
```

- [ ] **Step 5: Run the store test to verify it passes**

Run: `pytest tests/test_reasons.py -v`
Expected: the four store tests PASS.

- [ ] **Step 6: Create `app/routers/reasons.py`**

```python
"""Reasons CRUD endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_admin, require_client
from app.models import Reason, ReasonIn
from app.reasons_store import ReasonsStore

router = APIRouter(prefix="/reasons", tags=["reasons"])


def get_reasons_store() -> ReasonsStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("", dependencies=[Depends(require_client)])
def list_reasons(
    store: Annotated[ReasonsStore, Depends(get_reasons_store)],
) -> list[Reason]:
    return store.list_active()


@router.post(
    "", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)]
)
def create_reason(
    payload: ReasonIn,
    store: Annotated[ReasonsStore, Depends(get_reasons_store)],
) -> Reason:
    return store.add(payload.label)


@router.delete(
    "/{reason_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_reason(
    reason_id: str,
    store: Annotated[ReasonsStore, Depends(get_reasons_store)],
) -> None:
    if not store.deactivate(reason_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown reason")
```

- [ ] **Step 7: Wire the router in `app/main.py`**

Replace the contents of `app/main.py` with:

```python
"""FastAPI application factory and wiring."""
from app.config import get_settings
from fastapi import FastAPI

from app.reasons_store import ReasonsStore
from app.routers import health, reasons


def get_reasons_store() -> ReasonsStore:
    """Provide a reasons store backed by the configured file path."""
    return ReasonsStore(get_settings().reasons_file)


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(reasons.router)
    app.dependency_overrides[reasons.get_reasons_store] = get_reasons_store
    return app


app = create_app()
```

- [ ] **Step 8: Add a router-level fixture to `tests/conftest.py`**

Append to `tests/conftest.py`:

```python
from pathlib import Path

from app.config import Settings, get_settings
from app.reasons_store import ReasonsStore
from app.routers import reasons as reasons_router


@pytest.fixture
def configured_client(tmp_path: Path) -> TestClient:
    """A TestClient with temp-file stores and known tokens."""
    app = create_app()
    settings = Settings(
        admin_token="admin-secret",
        client_token="client-secret",
        reasons_file=tmp_path / "reasons.json",
        logo_dir=tmp_path / "logo",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[reasons_router.get_reasons_store] = (
        lambda: ReasonsStore(settings.reasons_file)
    )
    return TestClient(app)
```

- [ ] **Step 9: Add the endpoint tests to `tests/test_reasons.py`**

Append:

```python
ADMIN = {"X-Admin-Token": "admin-secret"}
CLIENT = {"X-Client-Token": "client-secret"}


def test_create_then_list_reason(configured_client):
    create = configured_client.post(
        "/reasons", json={"label": "Maintenance"}, headers=ADMIN
    )
    assert create.status_code == 201
    listing = configured_client.get("/reasons", headers=CLIENT)
    assert listing.status_code == 200
    assert [r["label"] for r in listing.json()] == ["Maintenance"]


def test_list_requires_client_token(configured_client):
    assert configured_client.get("/reasons").status_code == 401


def test_create_requires_admin_token(configured_client):
    assert (
        configured_client.post("/reasons", json={"label": "X"}, headers=CLIENT).status_code
        == 401
    )


def test_delete_unknown_reason_returns_404(configured_client):
    resp = configured_client.delete("/reasons/missing", headers=ADMIN)
    assert resp.status_code == 404
```

- [ ] **Step 10: Run all reasons tests to verify they pass**

Run: `pytest tests/test_reasons.py -v`
Expected: all store and endpoint tests PASS.

- [ ] **Step 11: Commit**

```bash
git add loginlogbook-api/app/models.py loginlogbook-api/app/reasons_store.py \
  loginlogbook-api/app/routers/reasons.py loginlogbook-api/app/main.py \
  loginlogbook-api/tests/conftest.py loginlogbook-api/tests/test_reasons.py
git commit -m "feat(api): add reasons store and CRUD endpoints"
```

---

### Task 4: InfluxDB wrapper

**Files:**
- Create: `loginlogbook-api/app/influx.py`
- Create: `loginlogbook-api/tests/test_influx_unit.py`

**Interfaces:**
- Consumes: `app.config.Settings`, `app.models.EventIn`, `app.models.EventOut`.
- Produces:
  - `app.influx.InfluxGateway(settings: Settings)` with methods:
    - `write_event(event: EventIn) -> None` — writes a point to `login_events`.
    - `recent_events(host: str, limit: int, event_type: str | None = None) -> list[EventOut]`
    - `ping() -> bool` — True if InfluxDB is reachable.
  - The gateway accepts an injectable low-level client so it can be unit-tested without a real database. Constructor signature: `InfluxGateway(settings, client_factory=default_client_factory)` where `client_factory(settings) -> InfluxDBClient`.

This task unit-tests the point-building logic with a fake client. A real-database integration test is Task 8.

- [ ] **Step 1: Write the failing test in `tests/test_influx_unit.py`**

```python
"""Unit tests for the InfluxDB gateway using a fake client."""
from datetime import datetime, timezone

from app.config import Settings
from app.influx import InfluxGateway
from app.models import EventIn


class FakeWriteApi:
    def __init__(self):
        self.written = []

    def write(self, bucket, org, record):
        self.written.append((bucket, org, record))


class FakeClient:
    def __init__(self):
        self._write_api = FakeWriteApi()

    def write_api(self, **kwargs):
        return self._write_api

    def ping(self):
        return True

    def close(self):
        pass


def _settings() -> Settings:
    return Settings(
        influx_bucket="logins", influx_org="loginlogbook", influx_token="t"
    )


def test_write_event_builds_point_with_tags():
    fake = FakeClient()
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    event = EventIn(
        event_type="login",
        host="srv01",
        os_user="alice",
        reason="Maintenance",
        timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    )
    gateway.write_event(event)
    assert len(fake._write_api.written) == 1
    bucket, org, point = fake._write_api.written[0]
    assert bucket == "logins"
    assert org == "loginlogbook"
    line = point.to_line_protocol()
    assert line.startswith("login_events,")
    assert "event_type=login" in line
    assert "host=srv01" in line
    assert "os_user=alice" in line
    assert "reason=Maintenance" in line


def test_ping_delegates_to_client():
    fake = FakeClient()
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    assert gateway.ping() is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_influx_unit.py -v`
Expected: FAIL with `ModuleNotFoundError: app.influx`.

- [ ] **Step 3: Create `app/influx.py`**

```python
"""InfluxDB access layer. The only module that talks to InfluxDB."""
from collections.abc import Callable

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import Settings
from app.models import EventIn, EventOut

MEASUREMENT = "login_events"


def default_client_factory(settings: Settings) -> InfluxDBClient:
    """Create a real InfluxDB client from settings."""
    return InfluxDBClient(
        url=settings.influx_url, token=settings.influx_token, org=settings.influx_org
    )


class InfluxGateway:
    """Reads and writes login_events points."""

    def __init__(
        self,
        settings: Settings,
        client_factory: Callable[[Settings], InfluxDBClient] = default_client_factory,
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory

    def write_event(self, event: EventIn) -> None:
        """Write a single login/logout event to InfluxDB."""
        point = (
            Point(MEASUREMENT)
            .tag("event_type", event.event_type)
            .tag("host", event.host)
            .tag("os_user", event.os_user)
            .field("count", 1)
            .time(event.timestamp, WritePrecision.NS)
        )
        if event.reason is not None:
            point = point.tag("reason", event.reason)

        client = self._client_factory(self._settings)
        try:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(
                bucket=self._settings.influx_bucket,
                org=self._settings.influx_org,
                record=point,
            )
        finally:
            client.close()

    def recent_events(
        self, host: str, limit: int, event_type: str | None = None
    ) -> list[EventOut]:
        """Return the most recent events for a host, newest first."""
        type_filter = (
            f' and r.event_type == "{event_type}"' if event_type else ""
        )
        flux = (
            f'from(bucket: "{self._settings.influx_bucket}")'
            f" |> range(start: -30d)"
            f' |> filter(fn: (r) => r._measurement == "{MEASUREMENT}"'
            f' and r.host == "{host}"{type_filter})'
            f" |> sort(columns: [\"_time\"], desc: true)"
            f" |> limit(n: {int(limit)})"
        )
        client = self._client_factory(self._settings)
        try:
            tables = client.query_api().query(flux, org=self._settings.influx_org)
        finally:
            client.close()

        events: list[EventOut] = []
        for table in tables:
            for record in table.records:
                events.append(
                    EventOut(
                        event_type=record.values.get("event_type"),
                        host=record.values.get("host"),
                        os_user=record.values.get("os_user"),
                        reason=record.values.get("reason"),
                        timestamp=record.get_time(),
                    )
                )
        return events

    def ping(self) -> bool:
        """Return True if InfluxDB responds to a ping."""
        client = self._client_factory(self._settings)
        try:
            return bool(client.ping())
        except Exception:
            return False
        finally:
            client.close()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_influx_unit.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-api/app/influx.py loginlogbook-api/tests/test_influx_unit.py
git commit -m "feat(api): add InfluxDB gateway for events"
```

---

### Task 5: Events router

**Files:**
- Create: `loginlogbook-api/app/routers/events.py`
- Modify: `loginlogbook-api/app/main.py`
- Modify: `loginlogbook-api/tests/conftest.py`
- Create: `loginlogbook-api/tests/test_events.py`

**Interfaces:**
- Consumes: `app.auth.require_client`, `app.influx.InfluxGateway`, `app.models.EventIn`, `app.models.EventOut`.
- Produces:
  - `app.routers.events.get_influx_gateway() -> InfluxGateway` dependency placeholder (overridden in `app.main`).
  - `POST /events` (client token) → 201, writes the event; returns 503 if the gateway raises.
  - `GET /events/recent?host=&limit=&event_type=` (client token) → list of `EventOut`; `limit` defaults to 5, capped at 100.

- [ ] **Step 1: Create `app/routers/events.py`**

```python
"""Event ingestion and recent-event query endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import require_client
from app.influx import InfluxGateway
from app.models import EventIn, EventOut

router = APIRouter(tags=["events"])


def get_influx_gateway() -> InfluxGateway:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_client)],
)
def record_event(
    event: EventIn,
    gateway: Annotated[InfluxGateway, Depends(get_influx_gateway)],
) -> dict[str, str]:
    try:
        gateway.write_event(event)
    except Exception as exc:  # InfluxDB unreachable or write failure
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event store unavailable",
        ) from exc
    return {"status": "recorded"}


@router.get(
    "/events/recent",
    dependencies=[Depends(require_client)],
)
def recent_events(
    gateway: Annotated[InfluxGateway, Depends(get_influx_gateway)],
    host: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 5,
    event_type: str | None = None,
) -> list[EventOut]:
    try:
        return gateway.recent_events(host=host, limit=limit, event_type=event_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event store unavailable",
        ) from exc
```

- [ ] **Step 2: Wire the events router in `app/main.py`**

In `app/main.py`, add the import and a gateway provider, and register the router. The full updated file:

```python
"""FastAPI application factory and wiring."""
from fastapi import FastAPI

from app.config import get_settings
from app.influx import InfluxGateway
from app.reasons_store import ReasonsStore
from app.routers import events, health, reasons


def get_reasons_store() -> ReasonsStore:
    """Provide a reasons store backed by the configured file path."""
    return ReasonsStore(get_settings().reasons_file)


def get_influx_gateway() -> InfluxGateway:
    """Provide an InfluxDB gateway backed by current settings."""
    return InfluxGateway(get_settings())


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(reasons.router)
    app.include_router(events.router)
    app.dependency_overrides[reasons.get_reasons_store] = get_reasons_store
    app.dependency_overrides[events.get_influx_gateway] = get_influx_gateway
    return app


app = create_app()
```

- [ ] **Step 3: Add a fake-gateway fixture to `tests/conftest.py`**

Append to `tests/conftest.py`:

```python
from app.influx import InfluxGateway
from app.models import EventIn, EventOut
from app.routers import events as events_router


class FakeGateway:
    """In-memory stand-in for InfluxGateway used in endpoint tests."""

    def __init__(self) -> None:
        self.events: list[EventIn] = []
        self.fail = False

    def write_event(self, event: EventIn) -> None:
        if self.fail:
            raise RuntimeError("influx down")
        self.events.append(event)

    def recent_events(self, host, limit, event_type=None) -> list[EventOut]:
        if self.fail:
            raise RuntimeError("influx down")
        items = [e for e in self.events if e.host == host]
        if event_type:
            items = [e for e in items if e.event_type == event_type]
        items = list(reversed(items))[:limit]
        return [
            EventOut(
                event_type=e.event_type,
                host=e.host,
                os_user=e.os_user,
                reason=e.reason,
                timestamp=e.timestamp,
            )
            for e in items
        ]

    def ping(self) -> bool:
        return not self.fail


@pytest.fixture
def fake_gateway() -> "FakeGateway":
    return FakeGateway()


@pytest.fixture
def events_client(tmp_path: Path, fake_gateway: "FakeGateway") -> TestClient:
    """A TestClient whose events use the in-memory fake gateway."""
    app = create_app()
    settings = Settings(
        admin_token="admin-secret",
        client_token="client-secret",
        reasons_file=tmp_path / "reasons.json",
        logo_dir=tmp_path / "logo",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[events_router.get_influx_gateway] = lambda: fake_gateway
    return TestClient(app)
```

- [ ] **Step 4: Write the failing tests in `tests/test_events.py`**

```python
"""Tests for the events endpoints."""

CLIENT = {"X-Client-Token": "client-secret"}


def _login_payload(host="srv01", user="alice", reason="Maintenance"):
    return {
        "event_type": "login",
        "host": host,
        "os_user": user,
        "reason": reason,
        "timestamp": "2026-06-26T08:00:00+00:00",
    }


def test_record_event_requires_client_token(events_client):
    assert events_client.post("/events", json=_login_payload()).status_code == 401


def test_record_event_succeeds(events_client):
    resp = events_client.post("/events", json=_login_payload(), headers=CLIENT)
    assert resp.status_code == 201


def test_record_event_returns_503_when_store_down(events_client, fake_gateway):
    fake_gateway.fail = True
    resp = events_client.post("/events", json=_login_payload(), headers=CLIENT)
    assert resp.status_code == 503


def test_recent_events_filters_by_host(events_client):
    events_client.post("/events", json=_login_payload(host="srv01"), headers=CLIENT)
    events_client.post("/events", json=_login_payload(host="srv02"), headers=CLIENT)
    resp = events_client.get("/events/recent", params={"host": "srv01"}, headers=CLIENT)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["host"] == "srv01"


def test_recent_events_respects_limit(events_client):
    for i in range(7):
        events_client.post(
            "/events", json=_login_payload(user=f"u{i}"), headers=CLIENT
        )
    resp = events_client.get(
        "/events/recent", params={"host": "srv01", "limit": 3}, headers=CLIENT
    )
    assert len(resp.json()) == 3
```

- [ ] **Step 5: Run the events tests to verify they pass**

Run: `pytest tests/test_events.py -v`
Expected: all five tests PASS.

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-api/app/routers/events.py loginlogbook-api/app/main.py \
  loginlogbook-api/tests/conftest.py loginlogbook-api/tests/test_events.py
git commit -m "feat(api): add event ingestion and recent-event endpoints"
```

---

### Task 6: Branding logo store and router

**Files:**
- Create: `loginlogbook-api/app/logo_store.py`
- Create: `loginlogbook-api/app/routers/branding.py`
- Modify: `loginlogbook-api/app/main.py`
- Create: `loginlogbook-api/tests/test_branding.py`

**Interfaces:**
- Consumes: `app.auth.require_admin`, `app.auth.require_client`, `app.config.Settings`.
- Produces:
  - `app.logo_store.LogoStore(logo_dir: Path, max_bytes: int)` with methods:
    - `save(content: bytes, content_type: str) -> None` — raises `ValueError` for an unsupported content type or oversized payload; stores the bytes plus its media type.
    - `load() -> tuple[bytes, str] | None` — returns `(content, content_type)` or `None` if no logo has been uploaded.
    - `ALLOWED = {"image/png": "logo.png", "image/svg+xml": "logo.svg"}` (class attribute).
  - `app.routers.branding.get_logo_store() -> LogoStore` placeholder (overridden in `app.main`).
  - `GET /branding/logo` (client token) → returns the image bytes with the correct media type, or 404 if none uploaded.
  - `PUT /branding/logo` (admin token, multipart file) → 204; 400 for unsupported type or oversize.

- [ ] **Step 1: Write the failing test in `tests/test_branding.py`**

```python
"""Tests for the logo store and branding endpoints."""
import pytest

from app.logo_store import LogoStore

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def test_save_and_load_png(tmp_path):
    store = LogoStore(tmp_path / "logo", max_bytes=2_097_152)
    store.save(PNG_BYTES, "image/png")
    loaded = store.load()
    assert loaded is not None
    content, content_type = loaded
    assert content == PNG_BYTES
    assert content_type == "image/png"


def test_load_returns_none_when_empty(tmp_path):
    store = LogoStore(tmp_path / "logo", max_bytes=2_097_152)
    assert store.load() is None


def test_save_rejects_unsupported_type(tmp_path):
    store = LogoStore(tmp_path / "logo", max_bytes=2_097_152)
    with pytest.raises(ValueError):
        store.save(b"data", "image/gif")


def test_save_rejects_oversize(tmp_path):
    store = LogoStore(tmp_path / "logo", max_bytes=10)
    with pytest.raises(ValueError):
        store.save(b"0" * 11, "image/png")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_branding.py -v`
Expected: FAIL with `ModuleNotFoundError: app.logo_store`.

- [ ] **Step 3: Create `app/logo_store.py`**

```python
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
```

- [ ] **Step 4: Run the store tests to verify they pass**

Run: `pytest tests/test_branding.py -v`
Expected: the four store tests PASS.

- [ ] **Step 5: Create `app/routers/branding.py`**

```python
"""Branding logo distribution endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status

from app.auth import require_admin, require_client
from app.logo_store import LogoStore

router = APIRouter(prefix="/branding", tags=["branding"])


def get_logo_store() -> LogoStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("/logo", dependencies=[Depends(require_client)])
def get_logo(store: Annotated[LogoStore, Depends(get_logo_store)]) -> Response:
    loaded = store.load()
    if loaded is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No logo set")
    content, content_type = loaded
    return Response(content=content, media_type=content_type)


@router.put(
    "/logo",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def put_logo(
    file: UploadFile,
    store: Annotated[LogoStore, Depends(get_logo_store)],
) -> None:
    content = await file.read()
    try:
        store.save(content, file.content_type or "")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
```

- [ ] **Step 6: Wire the branding router in `app/main.py`**

In `app/main.py`, add the import `from app.logo_store import LogoStore`, add `branding` to the `from app.routers import ...` line, add this provider:

```python
def get_logo_store() -> LogoStore:
    """Provide a logo store backed by current settings."""
    settings = get_settings()
    return LogoStore(settings.logo_dir, settings.logo_max_bytes)
```

and inside `create_app`, register the router and override its provider:

```python
    app.include_router(branding.router)
    app.dependency_overrides[branding.get_logo_store] = get_logo_store
```

- [ ] **Step 7: Add endpoint tests to `tests/test_branding.py`**

Append:

```python
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.logo_store import LogoStore
from app.main import create_app
from app.routers import branding as branding_router

ADMIN = {"X-Admin-Token": "admin-secret"}
CLIENT = {"X-Client-Token": "client-secret"}


def _branding_client(tmp_path: Path) -> TestClient:
    app = create_app()
    settings = Settings(
        admin_token="admin-secret",
        client_token="client-secret",
        reasons_file=tmp_path / "reasons.json",
        logo_dir=tmp_path / "logo",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[branding_router.get_logo_store] = lambda: LogoStore(
        settings.logo_dir, settings.logo_max_bytes
    )
    return TestClient(app)


def test_get_logo_404_when_unset(tmp_path):
    client = _branding_client(tmp_path)
    assert client.get("/branding/logo", headers=CLIENT).status_code == 404


def test_put_then_get_logo(tmp_path):
    client = _branding_client(tmp_path)
    upload = {"file": ("logo.png", BytesIO(PNG_BYTES), "image/png")}
    put = client.put("/branding/logo", files=upload, headers=ADMIN)
    assert put.status_code == 204
    got = client.get("/branding/logo", headers=CLIENT)
    assert got.status_code == 200
    assert got.content == PNG_BYTES
    assert got.headers["content-type"] == "image/png"


def test_put_logo_rejects_unsupported_type(tmp_path):
    client = _branding_client(tmp_path)
    upload = {"file": ("logo.gif", BytesIO(b"gif"), "image/gif")}
    resp = client.put("/branding/logo", files=upload, headers=ADMIN)
    assert resp.status_code == 400


def test_put_logo_requires_admin(tmp_path):
    client = _branding_client(tmp_path)
    upload = {"file": ("logo.png", BytesIO(PNG_BYTES), "image/png")}
    resp = client.put("/branding/logo", files=upload, headers=CLIENT)
    assert resp.status_code == 401
```

- [ ] **Step 8: Run all branding tests to verify they pass**

Run: `pytest tests/test_branding.py -v`
Expected: all store and endpoint tests PASS.

- [ ] **Step 9: Commit**

```bash
git add loginlogbook-api/app/logo_store.py loginlogbook-api/app/routers/branding.py \
  loginlogbook-api/app/main.py loginlogbook-api/tests/test_branding.py
git commit -m "feat(api): add central branding logo distribution"
```

---

### Task 7: Health readiness with InfluxDB ping

**Files:**
- Modify: `loginlogbook-api/app/routers/health.py`
- Modify: `loginlogbook-api/app/main.py`
- Modify: `loginlogbook-api/tests/test_health.py`

**Interfaces:**
- Consumes: `app.influx.InfluxGateway.ping`, the existing `get_influx_gateway` provider.
- Produces:
  - `GET /health` returns `{"status": "ok", "influxdb": "up"}` (200) when the gateway pings successfully, and `{"status": "degraded", "influxdb": "down"}` with HTTP 503 when it does not. Liveness still returns 200 only when InfluxDB is reachable; an unreachable database yields 503 so orchestration can detect it.
  - `app.routers.health.get_influx_gateway()` placeholder dependency (overridden in `app.main` with the same provider used by events).

- [ ] **Step 1: Update `tests/test_health.py` with the new expectations**

Replace the contents of `tests/test_health.py` with:

```python
"""Tests for the health endpoint."""
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.routers import health as health_router


class _Gateway:
    def __init__(self, up: bool) -> None:
        self._up = up

    def ping(self) -> bool:
        return self._up


def _health_client(up: bool) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings()
    app.dependency_overrides[health_router.get_influx_gateway] = lambda: _Gateway(up)
    return TestClient(app)


def test_health_ok_when_influx_up():
    resp = _health_client(up=True).get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "influxdb": "up"}


def test_health_503_when_influx_down():
    resp = _health_client(up=False).get("/health")
    assert resp.status_code == 503
    assert resp.json()["influxdb"] == "down"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_health.py -v`
Expected: FAIL — the current handler ignores InfluxDB and returns the old body.

- [ ] **Step 3: Update `app/routers/health.py`**

```python
"""Health endpoint with InfluxDB readiness."""
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.influx import InfluxGateway

router = APIRouter()


def get_influx_gateway() -> InfluxGateway:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("/health")
def health(
    response: Response,
    gateway: Annotated[InfluxGateway, Depends(get_influx_gateway)],
) -> dict[str, str]:
    """Readiness probe: ok only when InfluxDB is reachable."""
    if gateway.ping():
        return {"status": "ok", "influxdb": "up"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "influxdb": "down"}
```

- [ ] **Step 4: Override the health provider in `app/main.py`**

Inside `create_app`, after the existing overrides, add:

```python
    app.dependency_overrides[health.get_influx_gateway] = get_influx_gateway
```

(`get_influx_gateway` is already defined in `app/main.py` from Task 5.)

- [ ] **Step 5: Run the health tests to verify they pass**

Run: `pytest tests/test_health.py -v`
Expected: both tests PASS.

- [ ] **Step 6: Run the full suite (excluding the real-DB integration test)**

Run: `pytest -v --ignore=tests/test_integration_influx.py`
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-api/app/routers/health.py loginlogbook-api/app/main.py \
  loginlogbook-api/tests/test_health.py
git commit -m "feat(api): add InfluxDB readiness to health endpoint"
```

---

### Task 8: Docker packaging, compose, and InfluxDB integration test

**Files:**
- Create: `loginlogbook-api/Dockerfile`
- Create: `loginlogbook-api/docker-compose.yml`
- Create: `loginlogbook-api/.env.example`
- Create: `loginlogbook-api/tests/test_integration_influx.py`

**Interfaces:**
- Consumes: `app.config.Settings`, `app.influx.InfluxGateway`, `app.models.EventIn`.
- Produces: a runnable container stack and an integration test that writes and reads a real event. The integration test is skipped unless `LLB_INTEGRATION=1` and the InfluxDB env vars are set, so the normal suite stays hermetic.

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `.env.example`**

```dotenv
# InfluxDB connection (server-side only)
INFLUX_URL=http://influxdb:8086
INFLUX_TOKEN=replace-with-influx-token
INFLUX_ORG=loginlogbook
INFLUX_BUCKET=logins

# API access tokens
ADMIN_TOKEN=replace-with-admin-token
CLIENT_TOKEN=replace-with-client-token

# Persistence paths inside the container (mounted volume)
REASONS_FILE=/data/reasons.json
LOGO_DIR=/data/logo

# InfluxDB initial setup (used by the influxdb container on first start)
DOCKER_INFLUXDB_INIT_MODE=setup
DOCKER_INFLUXDB_INIT_USERNAME=admin
DOCKER_INFLUXDB_INIT_PASSWORD=replace-with-strong-password
DOCKER_INFLUXDB_INIT_ORG=loginlogbook
DOCKER_INFLUXDB_INIT_BUCKET=logins
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=replace-with-influx-token
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  influxdb:
    image: influxdb:2.7
    restart: unless-stopped
    environment:
      DOCKER_INFLUXDB_INIT_MODE: ${DOCKER_INFLUXDB_INIT_MODE}
      DOCKER_INFLUXDB_INIT_USERNAME: ${DOCKER_INFLUXDB_INIT_USERNAME}
      DOCKER_INFLUXDB_INIT_PASSWORD: ${DOCKER_INFLUXDB_INIT_PASSWORD}
      DOCKER_INFLUXDB_INIT_ORG: ${DOCKER_INFLUXDB_INIT_ORG}
      DOCKER_INFLUXDB_INIT_BUCKET: ${DOCKER_INFLUXDB_INIT_BUCKET}
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: ${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}
    volumes:
      - influx-data:/var/lib/influxdb2
    ports:
      - "8086:8086"

  api:
    build: .
    restart: unless-stopped
    depends_on:
      - influxdb
    environment:
      INFLUX_URL: ${INFLUX_URL}
      INFLUX_TOKEN: ${INFLUX_TOKEN}
      INFLUX_ORG: ${INFLUX_ORG}
      INFLUX_BUCKET: ${INFLUX_BUCKET}
      ADMIN_TOKEN: ${ADMIN_TOKEN}
      CLIENT_TOKEN: ${CLIENT_TOKEN}
      REASONS_FILE: ${REASONS_FILE}
      LOGO_DIR: ${LOGO_DIR}
    volumes:
      - api-data:/data
    ports:
      - "8000:8000"

volumes:
  influx-data:
  api-data:
```

- [ ] **Step 4: Create `tests/test_integration_influx.py`**

```python
"""Integration test against a real InfluxDB. Skipped unless explicitly enabled.

Enable with:
    LLB_INTEGRATION=1 INFLUX_URL=... INFLUX_TOKEN=... INFLUX_ORG=... \
    INFLUX_BUCKET=... pytest tests/test_integration_influx.py
"""
import os
import uuid
from datetime import datetime, timezone

import pytest

from app.config import Settings
from app.influx import InfluxGateway
from app.models import EventIn

pytestmark = pytest.mark.skipif(
    os.getenv("LLB_INTEGRATION") != "1",
    reason="integration test disabled (set LLB_INTEGRATION=1)",
)


def test_write_then_read_event():
    settings = Settings()  # reads INFLUX_* from environment
    gateway = InfluxGateway(settings)
    host = f"itest-{uuid.uuid4().hex[:8]}"
    event = EventIn(
        event_type="login",
        host=host,
        os_user="tester",
        reason="Integration",
        timestamp=datetime.now(timezone.utc),
    )
    gateway.write_event(event)

    recent = gateway.recent_events(host=host, limit=5)
    assert any(e.os_user == "tester" and e.reason == "Integration" for e in recent)
```

- [ ] **Step 5: Verify the normal suite still skips the integration test**

Run: `pytest -v`
Expected: all unit/endpoint tests PASS; `test_write_then_read_event` is SKIPPED.

- [ ] **Step 6: Manually verify the stack boots (optional but recommended)**

```bash
cp .env.example .env   # edit tokens/passwords first
docker compose up -d --build
curl -s http://localhost:8000/health
```
Expected: `{"status":"ok","influxdb":"up"}` once InfluxDB has finished initializing.

- [ ] **Step 7: Run the integration test against the running stack**

```bash
LLB_INTEGRATION=1 \
INFLUX_URL=http://localhost:8086 \
INFLUX_TOKEN=<DOCKER_INFLUXDB_INIT_ADMIN_TOKEN> \
INFLUX_ORG=loginlogbook INFLUX_BUCKET=logins \
pytest tests/test_integration_influx.py -v
```
Expected: `test_write_then_read_event PASSED`.

- [ ] **Step 8: Commit**

```bash
git add loginlogbook-api/Dockerfile loginlogbook-api/docker-compose.yml \
  loginlogbook-api/.env.example loginlogbook-api/tests/test_integration_influx.py
git commit -m "feat(api): add Docker packaging and InfluxDB integration test"
```

---

### Task 9: Security hardening — per-host tokens, rate limiting, and HTTPS

**Context for this task:** Three security requirements were added after the initial plan:

1. **Per-host client tokens** — instead of one shared `CLIENT_TOKEN`, the API accepts a list of tokens (one per client machine). Revoking a single compromised host does not affect other clients.
2. **Rate limiting** — each client token is limited to a sensible request rate to prevent abuse or runaway retry loops.
3. **HTTPS / TLS** — all traffic between clients and the API is encrypted via an nginx reverse proxy in the same Docker Compose stack.

InfluxDB remains unreachable from outside the Docker network (no port binding to the host). This was already the architecture; the nginx layer makes it explicit and enforced at the transport level.

**Files:**
- Modify: `loginlogbook-api/app/config.py`
- Modify: `loginlogbook-api/app/auth.py`
- Modify: `loginlogbook-api/app/main.py`
- Modify: `loginlogbook-api/docker-compose.yml`
- Modify: `loginlogbook-api/.env.example`
- Create: `loginlogbook-api/nginx/nginx.conf`
- Create: `loginlogbook-api/nginx/certs/` (placeholder — certs generated at deploy time)
- Modify: `loginlogbook-api/tests/conftest.py`
- Modify: `loginlogbook-api/tests/test_auth.py` (already exists from Task 2)

**Interfaces:**
- Consumes: `app.config.Settings`, `app.auth` module, `app.main.create_app`.
- Produces:
  - `Settings.client_tokens: list[str]` — parsed from env var `CLIENT_TOKENS` (comma-separated UUIDs). Falls back to `[CLIENT_TOKEN]` for backward compatibility.
  - `require_client` now accepts any token from `client_tokens`.
  - Rate limiter applied as FastAPI middleware: 60 requests/minute per token on client endpoints, 20 requests/minute per IP on admin endpoints.
  - nginx service in docker-compose handles TLS termination on port 443; API only listens on internal network port 8000.

- [ ] **Step 1: Add `slowapi` to dependencies**

In `loginlogbook-api/pyproject.toml`, add to `dependencies`:

```toml
"slowapi>=0.1.9",
```

- [ ] **Step 2: Write failing tests**

In `loginlogbook-api/tests/test_auth.py`, append:

```python
def test_multiple_client_tokens_both_accepted(configured_client):
    """Any token from CLIENT_TOKENS is accepted."""
    # The fixture sets CLIENT_TOKENS to two values; test with the second.
    second_token = "second-test-token"
    r = configured_client.get(
        "/reasons",
        headers={"X-Client-Token": second_token},
    )
    assert r.status_code == 200


def test_unknown_client_token_rejected(configured_client):
    r = configured_client.get(
        "/reasons",
        headers={"X-Client-Token": "not-a-known-token"},
    )
    assert r.status_code == 403
```

Create `loginlogbook-api/tests/test_rate_limit.py`:

```python
"""Tests for rate limiting middleware."""
from fastapi.testclient import TestClient

from app.main import create_app
from app.config import Settings


def _make_client(tokens: str = "tok") -> TestClient:
    s = Settings(
        client_tokens=tokens.split(","),
        admin_token="admin",
        influx_url="http://x",
        influx_token="x",
        influx_org="x",
        influx_bucket="x",
    )
    app = create_app(s)
    return TestClient(app, raise_server_exceptions=False)


def test_rate_limit_returns_429_after_burst():
    client = _make_client("tok")
    headers = {"X-Client-Token": "tok"}
    responses = [client.get("/reasons", headers=headers) for _ in range(65)]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes
```

- [ ] **Step 3: Run to verify failure**

```bash
pytest tests/test_auth.py::test_multiple_client_tokens_both_accepted \
       tests/test_auth.py::test_unknown_client_token_rejected \
       tests/test_rate_limit.py -v
```
Expected: FAIL.

- [ ] **Step 4: Update `app/config.py`** — add `client_tokens`

```python
from pydantic import field_validator

class Settings(BaseSettings):
    # ... existing fields ...

    # Support multiple per-host client tokens (comma-separated in env)
    client_tokens: list[str] = []

    # Legacy single-token env var — used as fallback if client_tokens is empty
    client_token: str = ""

    @field_validator("client_tokens", mode="before")
    @classmethod
    def _parse_tokens(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v

    def effective_client_tokens(self) -> list[str]:
        """Returns client_tokens if set, else [client_token] for backward compat."""
        return self.client_tokens if self.client_tokens else [self.client_token]
```

Add to `.env.example`:

```
# Per-host client tokens (comma-separated UUIDs — one per client machine)
# Generate with: python -c "import uuid; print(uuid.uuid4())"
CLIENT_TOKENS=<uuid-host1>,<uuid-host2>
```

- [ ] **Step 5: Update `app/auth.py`** — accept any token from the list

Replace the `require_client` dependency body:

```python
from fastapi import Depends, Header, HTTPException, status
from app.config import Settings


def require_client(
    x_client_token: str = Header(...),
    settings: Settings = Depends(get_settings),
) -> None:
    if x_client_token not in settings.effective_client_tokens():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
```

- [ ] **Step 6: Add rate limiting to `app/main.py`**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request


def _token_or_ip(request: Request) -> str:
    """Use client token as rate-limit key; fall back to IP."""
    return request.headers.get("x-client-token") or get_remote_address(request)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    limiter = Limiter(key_func=_token_or_ip, default_limits=["60/minute"])
    app = FastAPI(title="LoginLogBook API")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # ... rest of existing create_app body ...
    return app
```

Decorate the client-facing route functions with `@limiter.limit("60/minute")` and admin routes with `@limiter.limit("20/minute")`.

- [ ] **Step 7: Update `tests/conftest.py`** — set two client tokens in the fixture

```python
@pytest.fixture
def settings(tmp_path):
    return Settings(
        admin_token="test-admin-token",
        client_tokens=["test-client-token", "second-test-token"],
        influx_url="http://fake-influx",
        influx_token="fake",
        influx_org="test",
        influx_bucket="test",
        reasons_file=tmp_path / "reasons.json",
        logo_dir=tmp_path / "logo",
    )
```

- [ ] **Step 8: Run auth and rate-limit tests**

```bash
pytest tests/test_auth.py tests/test_rate_limit.py -v
```
Expected: all tests PASS.

- [ ] **Step 9: Add nginx TLS termination**

Create `loginlogbook-api/nginx/nginx.conf`:

```nginx
events {}

http {
    upstream api {
        server api:8000;
    }

    # Redirect HTTP → HTTPS
    server {
        listen 80;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        # Security headers
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;

        location / {
            proxy_pass         http://api;
            proxy_set_header   Host $host;
            proxy_set_header   X-Real-IP $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
            client_max_body_size 3m;    # logo upload: 2MB + overhead
        }
    }
}
```

- [ ] **Step 10: Update `docker-compose.yml`** — add nginx service, remove API port binding from host

```yaml
services:
  influxdb:
    image: influxdb:2.7
    restart: unless-stopped
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: ${INFLUX_ADMIN_USER}
      DOCKER_INFLUXDB_INIT_PASSWORD: ${INFLUX_ADMIN_PASSWORD}
      DOCKER_INFLUXDB_INIT_ORG: ${INFLUX_ORG}
      DOCKER_INFLUXDB_INIT_BUCKET: ${INFLUX_BUCKET}
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: ${INFLUX_TOKEN}
    volumes:
      - influxdb_data:/var/lib/influxdb2
    networks:
      - internal          # NOT exposed to host

  api:
    build: .
    restart: unless-stopped
    environment:
      INFLUX_URL: http://influxdb:8086
      INFLUX_TOKEN: ${INFLUX_TOKEN}
      INFLUX_ORG: ${INFLUX_ORG}
      INFLUX_BUCKET: ${INFLUX_BUCKET}
      ADMIN_TOKEN: ${ADMIN_TOKEN}
      CLIENT_TOKENS: ${CLIENT_TOKENS}
      REASONS_FILE: /data/reasons.json
      LOGO_DIR: /data/logo
    volumes:
      - api_data:/data
    networks:
      - internal          # NOT exposed to host
    depends_on:
      - influxdb

  nginx:
    image: nginx:1.27-alpine
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    networks:
      - internal
    depends_on:
      - api

volumes:
  influxdb_data:
  api_data:

networks:
  internal:
    driver: bridge
```

- [ ] **Step 11: Document cert generation in `.env.example`**

Append to `.env.example`:

```
# TLS certificates — place server.crt and server.key in nginx/certs/
# Self-signed (dev/internal):
#   openssl req -x509 -newkey rsa:4096 -keyout nginx/certs/server.key \
#     -out nginx/certs/server.crt -sha256 -days 3650 -nodes \
#     -subj "/CN=loginlogbook.internal"
# Production: use your internal CA or Let's Encrypt with certbot.
```

- [ ] **Step 12: Run full test suite**

```bash
pytest -v
```
Expected: all tests PASS.

- [ ] **Step 13: Smoke-test the secured stack**

```bash
# Generate a self-signed cert for local testing
mkdir -p nginx/certs
openssl req -x509 -newkey rsa:4096 -keyout nginx/certs/server.key \
  -out nginx/certs/server.crt -sha256 -days 365 -nodes \
  -subj "/CN=localhost"

cp .env.example .env  # fill in tokens
docker compose up -d --build
curl -sk https://localhost/health
```
Expected: `{"status":"ok","influxdb":"up"}`.

- [ ] **Step 14: Commit**

```bash
git add loginlogbook-api/app/config.py loginlogbook-api/app/auth.py \
  loginlogbook-api/app/main.py loginlogbook-api/docker-compose.yml \
  loginlogbook-api/.env.example loginlogbook-api/nginx/ \
  loginlogbook-api/tests/test_auth.py loginlogbook-api/tests/test_rate_limit.py \
  loginlogbook-api/tests/conftest.py loginlogbook-api/pyproject.toml
git commit -m "feat(api): add per-host tokens, rate limiting, and nginx HTTPS termination"
```

---

## Definition of Done (API)

- `pytest -v` passes; the integration test is skipped without `LLB_INTEGRATION=1`.
- `docker compose up --build` brings up `nginx` + `api` + `influxdb`; `GET https://localhost/health` returns 200 with `influxdb: up`.
- Endpoints implemented and tested: `GET /health`, `GET/POST/DELETE /reasons`, `POST /events`, `GET /events/recent`, `GET/PUT /branding/logo`.
- Admin endpoints require `X-Admin-Token`; client endpoints require any token from `CLIENT_TOKENS`.
- Rate limiting enforced: 429 returned after >60 requests/minute per client token; >20 requests/minute per IP on admin endpoints.
- All client↔API traffic is TLS-encrypted via nginx; InfluxDB is not reachable from outside the Docker network.
- No InfluxDB credentials are needed by, or exposed to, clients — only the API holds them.
- Each client machine uses its own unique token from `CLIENT_TOKENS`; revoking one token does not affect others.

This API plan establishes the concrete HTTP contract that the client and CLI
plans (Plan 2 and Plan 3) will consume.
