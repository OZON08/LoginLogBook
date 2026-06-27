"""Abmelden confirmation dialog (BITV SC 2.1.2: documented exit from overlay)."""
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ConfirmDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Abmelden bestätigen")
        self.setAccessibleName("Abmelden bestätigen")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("<b>Wirklich abmelden?</b>", self)
        title.setAccessibleName("Wirklich abmelden?")

        body = QLabel("Es wird kein Anmeldungsgrund erfasst.", self)

        buttons = QDialogButtonBox(self)
        btn_cancel = QPushButton("Abbrechen", self)
        btn_cancel.setDefault(True)
        btn_confirm = QPushButton("Abmelden", self)
        btn_confirm.setObjectName("btn_abmelden")
        btn_confirm.setAccessibleName("Abmelden bestätigen")

        buttons.addButton(btn_cancel, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton(btn_confirm, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(buttons)
