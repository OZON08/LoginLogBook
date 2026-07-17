"""Abmelden and Anmelden action buttons."""
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget
from PyQt6.QtCore import pyqtSignal

from app.i18n import t
from app.models import Reason


class ButtonRow(QWidget):
    anmelden_clicked = pyqtSignal(Reason)
    abmelden_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._reason: Reason | None = None
        self._loading = False

        self._btn_abmelden = QPushButton(self)
        self._btn_abmelden.setObjectName("btn_abmelden")
        self._btn_abmelden.clicked.connect(self.abmelden_clicked.emit)

        self._btn_anmelden = QPushButton(self)
        self._btn_anmelden.setObjectName("btn_anmelden")
        self._btn_anmelden.setEnabled(False)
        self._btn_anmelden.clicked.connect(self._on_anmelden)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._btn_abmelden)
        layout.addWidget(self._btn_anmelden)

        self.retranslate()

    def retranslate(self) -> None:
        self._btn_abmelden.setText(t("client.button.logout"))
        self._btn_abmelden.setAccessibleName(t("client.button.logout.noreason"))
        self._btn_anmelden.setAccessibleName(t("client.button.login"))
        self._btn_anmelden.setText("…" if self._loading else t("client.button.login"))

    def set_selected_reason(self, reason: Reason | None) -> None:
        self._reason = reason
        self._btn_anmelden.setEnabled(reason is not None)

    def set_loading(self, loading: bool) -> None:
        self._loading = loading
        self._btn_anmelden.setEnabled(not loading and self._reason is not None)
        self._btn_abmelden.setEnabled(not loading)
        self._btn_anmelden.setText("…" if loading else t("client.button.login"))

    def _on_anmelden(self) -> None:
        if self._reason is not None:
            self.anmelden_clicked.emit(self._reason)
