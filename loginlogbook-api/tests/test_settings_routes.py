import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(admin_token="admintok", client_tokens=["clienttok"],
                        settings_file=tmp_path / "settings.json")
    return TestClient(create_app(settings))


def test_get_settings_no_auth(client: TestClient):
    r = client.get("/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "de"
    assert "de" in body["available"] and "en" in body["available"]


def test_put_settings_requires_admin(client: TestClient):
    r = client.put("/settings", json={"language": "en"})
    assert r.status_code == 403


def test_put_settings_sets_language(client: TestClient):
    r = client.put("/settings", json={"language": "en"},
                   headers={"X-Admin-Token": "admintok"})
    assert r.status_code == 204
    assert client.get("/settings").json()["language"] == "en"


def test_put_settings_rejects_unknown_language(client: TestClient):
    r = client.put("/settings", json={"language": "xx"},
                   headers={"X-Admin-Token": "admintok"})
    assert r.status_code == 400


def test_get_admin_locale(client: TestClient):
    r = client.get("/locales/admin/de.json")
    assert r.status_code == 200
    assert "admin.tab.clients" in r.json()


def test_get_admin_locale_rejects_bad_code(client: TestClient):
    assert client.get("/locales/admin/../secrets.json").status_code == 404


def test_get_admin_locale_missing_returns_404(client: TestClient):
    # Valid two-letter code, but no such locale file exists.
    assert client.get("/locales/admin/fr.json").status_code == 404
