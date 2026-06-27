"""Filterable list of login reasons with BITV-compliant selection styling."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.models import Reason


class ReasonList(QWidget):
    selection_changed = pyqtSignal(object)  # emits Reason | None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._reasons: list[Reason] = []
        self._list = QListWidget(self)
        self._list.setObjectName("reason_list")
        self._list.setAccessibleName("Anmeldegrund auswählen")
        self._list.itemSelectionChanged.connect(self._on_selection_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

    def populate(self, reasons: list[Reason]) -> None:
        self._reasons = [r for r in reasons if r.active]
        self._render(self._reasons)

    def apply_filter(self, query: str) -> None:
        q = query.strip().lower()
        filtered = (
            [r for r in self._reasons if q in r.label.lower()]
            if q
            else list(self._reasons)
        )
        self._render(filtered)

    def _render(self, reasons: list[Reason]) -> None:
        self._list.clear()
        for r in reasons:
            item = QListWidgetItem(r.label)
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._list.addItem(item)

    def selected_reason(self) -> Reason | None:
        items = self._list.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.ItemDataRole.UserRole)

    def _on_selection_changed(self) -> None:
        self.selection_changed.emit(self.selected_reason())

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._list.setFocus()
            self._list.keyPressEvent(event)
        else:
            super().keyPressEvent(event)
