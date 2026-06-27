"""Search field with debounce and magnifier icon."""
from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from app.ui.styles import COLORS


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
        self._input.setPlaceholderText("Grund suchen…")
        self._input.textChanged.connect(self._debounce.start)
        self._input.setAccessibleName("Anmeldegrund suchen")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._input)

        # Install key filter for Escape
        self._input.installEventFilter(self)

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
