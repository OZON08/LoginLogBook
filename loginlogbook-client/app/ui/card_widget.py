"""Two-column card widget assembling all overlay sub-widgets."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.button_row import ButtonRow
from app.ui.footer_bar import FooterBar
from app.ui.logo_widget import LogoWidget
from app.ui.reason_list import ReasonList
from app.ui.recent_table import RecentTable
from app.ui.search_field import SearchField
from app.ui.styles import COLORS


class CardWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedWidth(920)

        self.logo = LogoWidget(self)
        self.search = SearchField(self)
        self.reason_list = ReasonList(self)
        self.button_row = ButtonRow(self)
        self.recent_table = RecentTable(self)
        self.footer = FooterBar(self)

        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(self.search)
        left_layout.addWidget(self.reason_list)
        left_layout.addStretch()
        left_layout.addWidget(self.button_row)

        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"color: {COLORS['border_ui']};")

        right = QWidget(self)
        right.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.recent_table)

        columns = QHBoxLayout()
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(24)
        columns.addWidget(left, 52)
        columns.addWidget(divider)
        columns.addWidget(right, 48)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(24)
        outer.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addLayout(columns)
        outer.addWidget(self.footer)

        self._apply_card_style()

    def _apply_card_style(self) -> None:
        self.setStyleSheet(
            f"QWidget#card {{ background-color: {COLORS['card_bg']};"
            "border-radius: 12px; }}"
        )
        self.setGraphicsEffect(self._make_shadow())

    def _make_shadow(self) -> QGraphicsDropShadowEffect:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(64)
        shadow.setOffset(0, 24)
        shadow.setColor(QColor(0, 0, 0, 90))
        return shadow
