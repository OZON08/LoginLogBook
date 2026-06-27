"""Shimmer skeleton placeholder widget shown while data is loading."""
from PyQt6.QtCore import QPropertyAnimation, QRect, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import QWidget

from app.ui.styles import COLORS


class SkeletonWidget(QWidget):
    """Animated shimmer rectangle used as a loading placeholder."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._shine_pos: float = -1.0
        self._anim = QPropertyAnimation(self, b"shine_pos", self)
        self._anim.setStartValue(-1.0)
        self._anim.setEndValue(2.0)
        self._anim.setDuration(1200)
        self._anim.setLoopCount(-1)
        self._anim.start()
        self.setMinimumHeight(20)

    @pyqtProperty(float)
    def shine_pos(self) -> float:
        return self._shine_pos

    @shine_pos.setter
    def shine_pos(self, value: float) -> None:
        self._shine_pos = value
        self.update()

    def set_geometry_hint(self, width: int, height: int) -> None:
        self.setFixedSize(width, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        grad = QLinearGradient(
            rect.width() * self._shine_pos - rect.width() * 0.3,
            0,
            rect.width() * self._shine_pos + rect.width() * 0.3,
            0,
        )
        grad.setColorAt(0.0, QColor(COLORS["skeleton"]))
        grad.setColorAt(0.5, QColor(COLORS["skeleton_shine"]))
        grad.setColorAt(1.0, QColor(COLORS["skeleton"]))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 6, 6)
