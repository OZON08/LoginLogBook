"""Shared test fixtures."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.models import EventIn, EventOut
from app.reasons_store import ReasonsStore
from app.routers import events as events_router
from app.routers import reasons as reasons_router


@pytest.fixture
def client() -> TestClient:
    """A TestClient bound to a fresh app instance."""
    return TestClient(create_app())


@pytest.fixture
def configured_client(tmp_path: Path) -> TestClient:
    """A TestClient with temp-file stores and known tokens."""
    app = create_app()
    settings = Settings(
        admin_token="admin-secret",
        client_token="client-secret",
        reasons_file=tmp_path / "reasons.json",
        logo_dir=tmp_path / "logo",
        clients_file=tmp_path / "clients.json",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[reasons_router.get_reasons_store] = (
        lambda: ReasonsStore(settings.reasons_file)
    )
    return TestClient(app)


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
def fake_gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def events_client(tmp_path: Path, fake_gateway: FakeGateway) -> TestClient:
    """A TestClient whose events use the in-memory fake gateway."""
    app = create_app()
    settings = Settings(
        admin_token="admin-secret",
        client_token="client-secret",
        reasons_file=tmp_path / "reasons.json",
        logo_dir=tmp_path / "logo",
        clients_file=tmp_path / "clients.json",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[events_router.get_influx_gateway] = lambda: fake_gateway
    return TestClient(app)
