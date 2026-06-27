"""Tests for the API client using httpx mock transport."""
from datetime import datetime, timezone

import httpx
import pytest

from app.api_client import ApiClient
from app.config import Settings
from app.models import AppConfig, EventIn, EventOut, Reason


def _client(transport: httpx.MockTransport) -> ApiClient:
    s = Settings(api_url="http://api", client_token="tok")
    return ApiClient(s, transport=transport)


def test_get_reasons_returns_list():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200, json=[{"id": "abc", "label": "Wartung", "active": True}]
        )
    )
    reasons = _client(transport).get_reasons()
    assert len(reasons) == 1
    assert reasons[0].label == "Wartung"


def test_get_reasons_sends_client_token():
    captured = {}

    def handler(req):
        captured["token"] = req.headers.get("x-client-token")
        return httpx.Response(200, json=[])

    _client(httpx.MockTransport(handler)).get_reasons()
    assert captured["token"] == "tok"


def test_get_logo_returns_bytes_and_content_type():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200, content=b"PNG", headers={"content-type": "image/png"}
        )
    )
    data, ct = _client(transport).get_logo()
    assert data == b"PNG"
    assert ct == "image/png"


def test_get_config_defaults():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"recent_days": 14})
    )
    cfg = _client(transport).get_config()
    assert cfg.recent_days == 14


def test_get_recent_events():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json=[
                {
                    "event_type": "login",
                    "host": "srv01",
                    "os_user": "alice",
                    "reason": "Wartung",
                    "timestamp": "2026-06-26T08:00:00+00:00",
                }
            ],
        )
    )
    events = _client(transport).get_recent_events("srv01", days=7)
    assert len(events) == 1
    assert events[0].reason == "Wartung"


def test_post_event_raises_on_error():
    transport = httpx.MockTransport(lambda req: httpx.Response(503))
    event = EventIn(
        event_type="login",
        host="srv01",
        os_user="alice",
        reason="Wartung",
        timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(httpx.HTTPStatusError):
        _client(transport).post_event(event)
