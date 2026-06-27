"""Tests for the recent logins table."""
from datetime import datetime, timezone

import pytest

from app.models import EventOut
from app.ui.recent_table import RecentTable


def _event(user: str, reason: str) -> EventOut:
    return EventOut(
        event_type="login",
        host="srv01",
        os_user=user,
        reason=reason,
        timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def table(qtbot):
    w = RecentTable()
    qtbot.addWidget(w)
    return w


def test_populate_sets_row_count(table):
    table.populate([_event("alice", "Wartung"), _event("bob", "Deployment")], days=7)
    assert table._table.rowCount() == 2


def test_populate_shows_username_in_second_column(table):
    table.populate([_event("alice", "Wartung")], days=7)
    assert table._table.item(0, 1).text() == "alice"


def test_populate_shows_reason_in_third_column(table):
    table.populate([_event("alice", "Wartung")], days=7)
    assert table._table.item(0, 2).text() == "Wartung"


def test_empty_events_shows_empty_label(table):
    table.populate([], days=7)
    assert table._empty_label.isVisible()
    assert table._table.rowCount() == 0
