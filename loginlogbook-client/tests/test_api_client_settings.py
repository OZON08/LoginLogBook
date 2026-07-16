"""Tests for ApiClient.get_settings() / LanguageSetting."""
import httpx

from app.api_client import ApiClient
from app.config import Settings
from app.models import LanguageSetting


def _client(transport: httpx.MockTransport) -> ApiClient:
    s = Settings(api_url="http://api", client_token="tok")
    return ApiClient(s, transport=transport)


def test_get_settings_parses():
    captured = {}

    def handler(req):
        captured["url"] = str(req.url)
        return httpx.Response(200, json={"language": "en", "available": ["de", "en"]})

    result = _client(httpx.MockTransport(handler)).get_settings()

    assert captured["url"].endswith("/settings")
    assert isinstance(result, LanguageSetting)
    assert result.language == "en"
    assert result.available == ["de", "en"]
