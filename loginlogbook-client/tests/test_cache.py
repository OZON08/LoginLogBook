"""Tests for CacheStore."""
from datetime import datetime, timezone
from pathlib import Path

from app.cache import CacheStore
from app.models import AppConfig, EventOut, Reason


def test_reasons_round_trip(tmp_path):
    store = CacheStore(tmp_path)
    reasons = [Reason(id="1", label="Wartung"), Reason(id="2", label="Deployment")]
    store.save_reasons(reasons)
    loaded = store.load_reasons()
    assert loaded is not None
    assert [r.label for r in loaded] == ["Wartung", "Deployment"]


def test_load_reasons_returns_none_when_empty(tmp_path):
    assert CacheStore(tmp_path).load_reasons() is None


def test_logo_round_trip(tmp_path):
    store = CacheStore(tmp_path)
    store.save_logo(b"PNG", "image/png")
    data, ct = store.load_logo()
    assert data == b"PNG"
    assert ct == "image/png"


def test_load_logo_returns_none_when_empty(tmp_path):
    assert CacheStore(tmp_path).load_logo() is None


def test_config_round_trip(tmp_path):
    store = CacheStore(tmp_path)
    store.save_config(AppConfig(recent_days=14))
    cfg = store.load_config()
    assert cfg is not None
    assert cfg.recent_days == 14


def test_recent_events_round_trip(tmp_path):
    store = CacheStore(tmp_path)
    events = [
        EventOut(
            event_type="login",
            host="srv01",
            os_user="alice",
            reason="Wartung",
            timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
        )
    ]
    store.save_recent_events(events)
    loaded = store.load_recent_events()
    assert loaded is not None
    assert loaded[0].reason == "Wartung"
