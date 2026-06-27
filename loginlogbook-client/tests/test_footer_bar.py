"""Tests for the footer bar status indicator."""
import pytest

from app.ui.footer_bar import FooterBar
from app.ui.styles import COLORS


@pytest.fixture
def footer(qtbot):
    w = FooterBar()
    qtbot.addWidget(w)
    return w


def test_set_user_host_updates_label(footer):
    footer.set_user_host("karsten", "SRV01")
    assert "karsten" in footer._user_label.text()
    assert "SRV01" in footer._user_label.text()


def test_online_status_shows_text(footer):
    footer.set_status(online=True)
    assert "Online" in footer._status_label.text()


def test_offline_status_shows_text(footer):
    footer.set_status(online=False)
    assert "Offline" in footer._status_label.text()


def test_status_label_has_accessible_name(footer):
    footer.set_status(online=True)
    assert footer._status_label.accessibleName() != ""
