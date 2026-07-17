"""Search field with debounce and Escape-to-clear."""
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from app.i18n import t


class SearchField(QWidget):
    filter_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self._emit)

        self._input = QLineEdit(self)
        self._input.setObjectName("search_field")
        self._input.textChanged.connect(self._debounce.start)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._input)

        self._input.installEventFilter(self)

        self.retranslate()

    def retranslate(self) -> None:
        self._input.setPlaceholderText(t("client.reason.search.placeholder"))
        self._input.setAccessibleName(t("client.reason.search"))

    def eventFilter(self, obj, event) -> bool:
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._input.clear()
                self.filter_changed.emit("")
                return True
        return super().eventFilter(obj, event)

    def _emit(self) -> None:
        self.filter_changed.emit(self._input.text())

    def clear(self) -> None:
        self._input.clear()

    def set_focus(self) -> None:
        self._input.setFocus()
