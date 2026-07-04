"""Tests for the logo store and branding endpoints."""
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.logo_store import LogoStore
from app.main import create_app
from app.routers import branding as branding_router

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32

ADMIN = {"X-Admin-Token": "admin-secret"}
CLIENT = {"X-Client-Token": "client-secret"}


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
    assert resp.status_code == 403


def test_get_logo_requires_client_token(tmp_path):
    client = _branding_client(tmp_path)
    assert client.get("/branding/logo").status_code == 403
