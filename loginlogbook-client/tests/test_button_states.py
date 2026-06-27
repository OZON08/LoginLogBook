"""Tests for ButtonRow enable/disable and signal emission."""
import pytest
from PyQt6.QtWidgets import QApplication

from app.models import Reason
from app.ui.button_row import ButtonRow


@pytest.fixture
def row(qtbot):
    widget = ButtonRow()
    qtbot.addWidget(widget)
    return widget


def test_anmelden_disabled_initially(row):
    assert not row._btn_anmelden.isEnabled()


def test_anmelden_enabled_after_reason_set(row):
    row.set_selected_reason(Reason(id="1", label="Wartung"))
    assert row._btn_anmelden.isEnabled()


def test_anmelden_disabled_after_reason_cleared(row):
    row.set_selected_reason(Reason(id="1", label="Wartung"))
    row.set_selected_reason(None)
    assert not row._btn_anmelden.isEnabled()


def test_anmelden_emits_signal_with_reason(row, qtbot):
    reason = Reason(id="1", label="Wartung")
    row.set_selected_reason(reason)
    with qtbot.waitSignal(row.anmelden_clicked, timeout=500) as blocker:
        row._btn_anmelden.click()
    assert blocker.args[0].label == "Wartung"


def test_abmelden_emits_signal(row, qtbot):
    with qtbot.waitSignal(row.abmelden_clicked, timeout=500):
        row._btn_abmelden.click()


def test_set_loading_disables_both_buttons(row):
    row.set_selected_reason(Reason(id="1", label="Wartung"))
    row.set_loading(True)
    assert not row._btn_anmelden.isEnabled()
    assert not row._btn_abmelden.isEnabled()


def test_anmelden_stays_disabled_after_loading_clears_without_reason(row):
    row.set_loading(True)
    row.set_loading(False)
    assert not row._btn_anmelden.isEnabled()
