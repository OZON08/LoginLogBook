"""Tests for EventQueue."""
from datetime import datetime, timezone

import pytest

from app.event_queue import EventQueue
from app.models import EventIn


def _event(user: str = "alice") -> EventIn:
    return EventIn(
        event_type="login",
        host="srv01",
        os_user=user,
        reason="Wartung",
        timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    )


def test_enqueue_increases_count(tmp_path):
    q = EventQueue(tmp_path / "queue.json")
    assert q.pending_count() == 0
    q.enqueue(_event())
    assert q.pending_count() == 1


def test_flush_sends_all_and_clears(tmp_path):
    q = EventQueue(tmp_path / "queue.json")
    q.enqueue(_event("alice"))
    q.enqueue(_event("bob"))
    sent_events = []
    sent = q.flush(lambda e: sent_events.append(e))
    assert sent == 2
    assert q.pending_count() == 0
    assert {e.os_user for e in sent_events} == {"alice", "bob"}


def test_flush_keeps_failed_events(tmp_path):
    q = EventQueue(tmp_path / "queue.json")
    q.enqueue(_event())

    def failing_post(e: EventIn) -> None:
        raise RuntimeError("network down")

    sent = q.flush(failing_post)
    assert sent == 0
    assert q.pending_count() == 1


def test_flush_on_empty_queue_returns_zero(tmp_path):
    q = EventQueue(tmp_path / "queue.json")
    assert q.flush(lambda e: None) == 0
