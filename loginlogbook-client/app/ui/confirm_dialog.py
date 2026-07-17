"""Abmelden confirmation dialog (BITV SC 2.1.2: documented exit from overlay)."""
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.i18n import t


class ConfirmDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        self._title = QLabel(self)

        self._body = QLabel(self)

        buttons = QDialogButtonBox(self)
        self._btn_cancel = QPushButton(self)
        self._btn_cancel.setDefault(True)
        self._btn_confirm = QPushButton(self)
        self._btn_confirm.setObjectName("btn_abmelden")

        buttons.addButton(self._btn_cancel, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton(self._btn_confirm, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(self._title)
        layout.addWidget(self._body)
        layout.addWidget(buttons)

        self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(t("client.confirm.logout.title"))
        self.setAccessibleName(t("client.confirm.logout.title"))
        self._title.setText(f"<b>{t('client.confirm.logout.question')}</b>")
        self._title.setAccessibleName(t("client.confirm.logout.question"))
        self._body.setText(t("client.freetext.none"))
        self._btn_cancel.setText(t("client.confirm.cancel"))
        self._btn_confirm.setText(t("client.button.logout"))
        self._btn_confirm.setAccessibleName(t("client.confirm.logout.title"))
