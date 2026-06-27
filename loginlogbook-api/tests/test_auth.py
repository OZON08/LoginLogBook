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
