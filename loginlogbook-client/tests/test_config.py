"""Tests for Settings."""
from pathlib import Path

from app.config import Settings


def test_settings_defaults():
    s = Settings(api_url="http://x", client_token="tok")
    assert s.api_url == "http://x"
    assert isinstance(s.cache_dir, Path)


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("API_URL", "http://custom:8000")
    monkeypatch.setenv("CLIENT_TOKEN", "mytoken")
    s = Settings()
    assert s.api_url == "http://custom:8000"
    assert s.client_token == "mytoken"


def test_api_ca_bundle_defaults_to_none():
    s = Settings(api_url="http://x", client_token="tok")
    assert s.api_ca_bundle is None


def test_api_ca_bundle_can_be_set():
    ca_path = Path("/etc/ssl/certs/ca.pem")
    s = Settings(api_url="http://x", client_token="tok", api_ca_bundle=ca_path)
    assert s.api_ca_bundle == ca_path
