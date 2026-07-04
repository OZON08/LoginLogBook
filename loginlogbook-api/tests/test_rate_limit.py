"""Tests for API rate limiting."""
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.routers import health as health_router


class _AlwaysUpGateway:
    def ping(self) -> bool:
        return True


def _rate_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        admin_token="admin-secret",
        client_tokens=["client-secret"],
    )
    app.dependency_overrides[health_router.get_influx_gateway] = lambda: _AlwaysUpGateway()
    return TestClient(app, raise_server_exceptions=False)


def test_rate_limit_returns_429_after_burst():
    client = _rate_client()
    headers = {"X-Client-Token": "client-secret"}
    responses = [client.get("/health", headers=headers) for _ in range(65)]
    assert any(r.status_code == 429 for r in responses)
