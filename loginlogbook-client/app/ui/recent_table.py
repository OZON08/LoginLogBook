"""Table showing recent login events for this host."""
from datetime import datetime, timezone

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import EventOut
from app.ui.skeleton import SkeletonWidget
from app.ui.styles import COLORS


class RecentTable(QWidget):
    _HEADERS = ["Datum / Uhrzeit", "Benutzer", "Grund"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Letzte Anmeldungen")

        self._header_label = QLabel("Letzte Anmeldungen", self)
        self._header_label.setStyleSheet(
            "font-size: 16px; font-weight: 600;"
        )
        self._days_label = QLabel("", self)
        self._days_label.setStyleSheet(f"font-size: 13px; color: {COLORS['muted']};")

        self._skeleton = SkeletonWidget(self)
        self._skeleton.set_geometry_hint(400, 120)

        self._table = QTableWidget(0, 3, self)
        self._table.setObjectName("recent_table")
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setAccessibleName("Tabelle der letzten Anmeldungen")

        self._empty_label = QLabel("Keine Anmeldungen in diesem Zeitraum", self)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        self._empty_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._header_label)
        layout.addWidget(self._days_label)
        layout.addWidget(self._skeleton)
        layout.addWidget(self._table)
        layout.addWidget(self._empty_label)

        self.setVisible(True)
        self.set_loading(True)

    def set_loading(self, loading: bool) -> None:
        self._skeleton.setVisible(loading)
        self._table.setVisible(not loading)

    def populate(self, events: list[EventOut], days: int) -> None:
        self._days_label.setText(f"Letzte {days} Tage")
        self._table.setRowCount(0)
        self.set_loading(False)

        if not events:
            self._empty_label.setVisible(True)
            self._table.setVisible(False)
            return

        self._empty_label.setVisible(False)
        self._table.setVisible(True)
        for event in sorted(events, key=lambda e: e.timestamp, reverse=True):
            row = self._table.rowCount()
            self._table.insertRow(row)
            ts = event.timestamp.astimezone().strftime("%d.%m.%Y %H:%M")
            for col, text in enumerate([ts, event.os_user, event.reason or ""]):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row, col, item)
