"""Tests for the client store."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.client_store import ClientStore
from app.config import Settings, get_settings
from app.main import create_app
from app.routers import clients as clients_router


def test_tokens_empty_when_file_missing(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    assert store.tokens() == []


def test_list_names_empty_when_file_missing(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    assert store.list_names() == []


def test_add_and_list(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    store.add("ws-01", "token-a")
    assert store.list_names() == ["ws-01"]
    assert store.tokens() == ["token-a"]


def test_add_duplicate_name_raises(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    store.add("ws-01", "token-a")
    with pytest.raises(ValueError, match="ws-01"):
        store.add("ws-01", "token-b")


def test_remove_existing_returns_true(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    store.add("ws-01", "token-a")
    assert store.remove("ws-01") is True
    assert store.list_names() == []


def test_remove_unknown_returns_false(tmp_path: Path):
    store = ClientStore(tmp_path / "clients.json")
    assert store.remove("does-not-exist") is False


def test_persists_across_instances(tmp_path: Path):
    path = tmp_path / "clients.json"
    ClientStore(path).add("ws-01", "token-a")
    assert ClientStore(path).list_names() == ["ws-01"]


ADMIN = {"X-Admin-Token": "admin-secret"}


def _clients_app(tmp_path: Path) -> TestClient:
    from app.reasons_store import ReasonsStore
    from app.routers import reasons as reasons_router

    app = create_app()
    settings = Settings(
        admin_token="admin-secret",
        client_token="client-secret",
        clients_file=tmp_path / "clients.json",
        reasons_file=tmp_path / "reasons.json",
        logo_dir=tmp_path / "logo",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[clients_router.get_client_store] = lambda: ClientStore(
        settings.clients_file
    )
    app.dependency_overrides[reasons_router.get_reasons_store] = lambda: ReasonsStore(
        settings.reasons_file
    )
    return TestClient(app)


def test_list_clients_empty(tmp_path):
    client = _clients_app(tmp_path)
    resp = client.get("/clients", headers=ADMIN)
    assert resp.status_code == 200
    assert resp.json() == []


def test_register_client(tmp_path):
    client = _clients_app(tmp_path)
    resp = client.post("/clients", json={"name": "ws-01", "token": "abc"}, headers=ADMIN)
    assert resp.status_code == 201
    assert resp.json() == {"name": "ws-01"}


def test_register_returns_name_not_token(tmp_path):
    client = _clients_app(tmp_path)
    resp = client.post("/clients", json={"name": "ws-01", "token": "secret"}, headers=ADMIN)
    assert "token" not in resp.json()


def test_list_shows_registered_name(tmp_path):
    client = _clients_app(tmp_path)
    client.post("/clients", json={"name": "ws-01", "token": "abc"}, headers=ADMIN)
    resp = client.get("/clients", headers=ADMIN)
    assert [c["name"] for c in resp.json()] == ["ws-01"]


def test_duplicate_name_returns_409(tmp_path):
    client = _clients_app(tmp_path)
    client.post("/clients", json={"name": "ws-01", "token": "abc"}, headers=ADMIN)
    resp = client.post("/clients", json={"name": "ws-01", "token": "def"}, headers=ADMIN)
    assert resp.status_code == 409


def test_delete_client(tmp_path):
    client = _clients_app(tmp_path)
    client.post("/clients", json={"name": "ws-01", "token": "abc"}, headers=ADMIN)
    resp = client.delete("/clients/ws-01", headers=ADMIN)
    assert resp.status_code == 204
    assert client.get("/clients", headers=ADMIN).json() == []


def test_delete_unknown_returns_404(tmp_path):
    client = _clients_app(tmp_path)
    resp = client.delete("/clients/no-such-client", headers=ADMIN)
    assert resp.status_code == 404


def test_clients_endpoints_require_admin(tmp_path):
    client = _clients_app(tmp_path)
    assert client.get("/clients").status_code == 403
    assert client.post("/clients", json={"name": "x", "token": "y"}).status_code == 403
    assert client.delete("/clients/x").status_code == 403


def test_registered_token_accepted_for_client_auth(tmp_path):
    client = _clients_app(tmp_path)
    client.post("/clients", json={"name": "ws-01", "token": "new-token"}, headers=ADMIN)
    resp = client.get("/reasons", headers={"X-Client-Token": "new-token"})
    assert resp.status_code == 200


def test_revoked_token_is_rejected(tmp_path):
    client = _clients_app(tmp_path)
    client.post("/clients", json={"name": "ws-01", "token": "new-token"}, headers=ADMIN)
    assert client.get("/reasons", headers={"X-Client-Token": "new-token"}).status_code == 200
    client.delete("/clients/ws-01", headers=ADMIN)
    assert client.get("/reasons", headers={"X-Client-Token": "new-token"}).status_code == 403
