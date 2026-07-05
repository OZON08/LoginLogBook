"""Tests for token authentication dependencies."""
import tempfile
from pathlib import Path

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

    _td = tempfile.TemporaryDirectory()
    app._tempdir = _td  # keep reference alive — cleaned up when app is GC'd
    _clients_path = Path(_td.name) / "clients.json"
    app.dependency_overrides[get_settings] = lambda: Settings(
        admin_token="admin-secret",
        client_token="client-secret",
        clients_file=_clients_path,
    )
    return app


def test_admin_route_rejects_missing_token():
    client = TestClient(_app_with_protected_routes())
    assert client.get("/admin-only").status_code == 403


def test_admin_route_rejects_wrong_token():
    client = TestClient(_app_with_protected_routes())
    resp = client.get("/admin-only", headers={"X-Admin-Token": "nope"})
    assert resp.status_code == 403


def test_admin_route_accepts_correct_token():
    client = TestClient(_app_with_protected_routes())
    resp = client.get("/admin-only", headers={"X-Admin-Token": "admin-secret"})
    assert resp.status_code == 200


def test_client_route_accepts_correct_token():
    client = TestClient(_app_with_protected_routes())
    resp = client.get("/client-only", headers={"X-Client-Token": "client-secret"})
    assert resp.status_code == 200


def test_multiple_client_tokens_both_accepted(tmp_path):
    app = FastAPI()

    @app.get("/client-only", dependencies=[Depends(auth.require_client)])
    def client_only() -> dict[str, bool]:
        return {"ok": True}

    app.dependency_overrides[get_settings] = lambda: Settings(
        admin_token="admin-secret",
        client_tokens=["token-a", "token-b"],
        clients_file=tmp_path / "clients.json",
    )
    client = TestClient(app)
    assert client.get("/client-only", headers={"X-Client-Token": "token-a"}).status_code == 200
    assert client.get("/client-only", headers={"X-Client-Token": "token-b"}).status_code == 200


def test_unknown_client_token_rejected():
    client = TestClient(_app_with_protected_routes())
    resp = client.get("/client-only", headers={"X-Client-Token": "not-a-valid-token"})
    assert resp.status_code == 403


def test_file_client_token_accepted(tmp_path):
    from app.client_store import ClientStore

    clients_file = tmp_path / "clients.json"
    store = ClientStore(clients_file)
    store.add("ws-01", "file-token")

    app = _app_with_protected_routes()
    app.dependency_overrides[get_settings] = lambda: Settings(
        admin_token="admin-secret",
        client_token="",
        clients_file=clients_file,
    )
    app.dependency_overrides[auth.get_client_store] = lambda: store
    client = TestClient(app)
    assert client.get("/client-only", headers={"X-Client-Token": "file-token"}).status_code == 200
