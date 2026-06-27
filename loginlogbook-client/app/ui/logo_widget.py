"""Branding logo widget: shows API logo, skeleton while loading, or fallback text."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.skeleton import SkeletonWidget


class LogoWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Firmenlogo")
        self.setMaximumHeight(80)

        self._skeleton = SkeletonWidget(self)
        self._skeleton.set_geometry_hint(160, 56)

        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMaximumHeight(72)
        self._image_label.setVisible(False)

        self._fallback_label = QLabel("LoginLogBook", self)
        self._fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fallback_label.setStyleSheet(
            "font-size: 22px; font-weight: 600; color: #0F172A;"
        )
        self._fallback_label.setAccessibleName("LoginLogBook")
        self._fallback_label.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._skeleton, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._image_label)
        layout.addWidget(self._fallback_label)

    def set_loading(self, loading: bool) -> None:
        self._skeleton.setVisible(loading)
        if not loading and not self._image_label.isVisible():
            self._fallback_label.setVisible(True)

    def set_logo(self, data: bytes, content_type: str) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        scaled = pixmap.scaledToHeight(
            64, Qt.TransformationMode.SmoothTransformation
        )
        self._image_label.setPixmap(scaled)
        self._image_label.setVisible(True)
        self._skeleton.setVisible(False)
        self._fallback_label.setVisible(False)
