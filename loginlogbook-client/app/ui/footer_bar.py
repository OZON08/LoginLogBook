"""Footer bar showing current user/host and API connection status."""
from importlib.metadata import version as _pkg_version

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui.styles import COLORS

try:
    _VERSION = _pkg_version("loginlogbook-client")
except Exception:
    _VERSION = "?"


class FooterBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._user_label = QLabel("", self)
        self._user_label.setStyleSheet(
            f"font-size: 12px; color: {COLORS['muted']};"
        )
        self._user_label.setAccessibleName("Angemeldeter Benutzer und Hostname")

        self._license_label = QLabel(f"© 2026 OZON08 · MIT License · v{_VERSION}", self)
        self._license_label.setStyleSheet(f"font-size: 11px; color: {COLORS['muted']};")
        self._license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._status_label = QLabel("", self)
        self._status_label.setStyleSheet(f"font-size: 12px; color: {COLORS['muted']};")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(self._user_label)
        layout.addStretch()
        layout.addWidget(self._license_label)
        layout.addStretch()
        layout.addWidget(self._status_label)

    def set_user_host(self, user: str, host: str) -> None:
        self._user_label.setText(f"{user} · {host}")

    def set_status(self, online: bool) -> None:
        if online:
            dot = f'<span style="color:{COLORS["status_online"]};">●</span>'
            text = f"{dot} Online"
            accessible = "Verbindungsstatus: Online"
        else:
            dot = f'<span style="color:{COLORS["status_offline"]};">●</span>'
            text = f"{dot} Offline – Cache"
            accessible = "Verbindungsstatus: Offline, zwischengespeicherte Daten"
        self._status_label.setText(text)
        self._status_label.setTextFormat(Qt.TextFormat.RichText)
        self._status_label.setAccessibleName(accessible)
