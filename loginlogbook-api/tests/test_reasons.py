"""Tests for the reasons store and reasons endpoints."""
from pathlib import Path

from app.reasons_store import ReasonsStore

ADMIN = {"X-Admin-Token": "admin-secret"}
CLIENT = {"X-Client-Token": "client-secret"}


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


def test_create_then_list_reason(configured_client):
    create = configured_client.post(
        "/reasons", json={"label": "Maintenance"}, headers=ADMIN
    )
    assert create.status_code == 201
    listing = configured_client.get("/reasons", headers=CLIENT)
    assert listing.status_code == 200
    assert [r["label"] for r in listing.json()] == ["Maintenance"]


def test_list_requires_client_token(configured_client):
    assert configured_client.get("/reasons").status_code == 403


def test_create_requires_admin_token(configured_client):
    assert (
        configured_client.post("/reasons", json={"label": "X"}, headers=CLIENT).status_code
        == 403
    )


def test_delete_unknown_reason_returns_404(configured_client):
    resp = configured_client.delete("/reasons/missing", headers=ADMIN)
    assert resp.status_code == 404
