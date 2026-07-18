from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client(tmp_path: Path, language: str = "de") -> TestClient:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(f'{{"language": "{language}"}}', encoding="utf-8")
    settings = Settings(admin_token="admintok", client_tokens=["clienttok"],
                        settings_file=settings_file)
    return TestClient(create_app(settings), raise_server_exceptions=False)


def test_html_404_is_localized_german(tmp_path: Path):
    client = _client(tmp_path, "de")
    r = client.get("/does-not-exist", headers={"Accept": "text/html"})
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
    assert "Seite nicht gefunden" in r.text
    assert "data:image/svg+xml;base64," in r.text  # embedded logo


def test_html_404_is_localized_english(tmp_path: Path):
    client = _client(tmp_path, "en")
    r = client.get("/does-not-exist", headers={"Accept": "text/html"})
    assert r.status_code == 404
    assert "Page not found" in r.text


def test_api_client_still_gets_json(tmp_path: Path):
    client = _client(tmp_path, "de")
    r = client.get("/does-not-exist")  # no text/html in Accept
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    assert "detail" in r.json()
