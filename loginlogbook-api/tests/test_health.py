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
