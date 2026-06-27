"""Design token colors and Qt stylesheet for the entire overlay."""

COLORS: dict[str, str] = {
    "overlay_bg": "rgba(15, 23, 42, 224)",   # 0.88 * 255 ≈ 224
    "card_bg": "#FFFFFF",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "foreground": "#0F172A",
    "muted": "#475569",
    "border_decorative": "#E2E8F0",
    "border_ui": "#6B7280",
    "selection_bg": "#EFF6FF",
    "selection_border": "#2563EB",
    "destructive": "#DC2626",
    "status_online": "#16A34A",
    "status_offline": "#CA8A04",
    "skeleton": "#E2E8F0",
    "skeleton_shine": "#F8FAFC",
}

STYLESHEET = f"""
QWidget {{
    font-family: "Segoe UI", system-ui, sans-serif;
    color: {COLORS["foreground"]};
}}

QWidget#card {{
    background-color: {COLORS["card_bg"]};
    border-radius: 12px;
}}

QLineEdit#search_field {{
    border: 1px solid {COLORS["border_ui"]};
    border-radius: 6px;
    padding: 8px 8px 8px 36px;
    font-size: 15px;
    background: {COLORS["card_bg"]};
    min-height: 44px;
}}

QLineEdit#search_field:focus {{
    border: 2px solid {COLORS["primary"]};
}}

QListWidget#reason_list {{
    border: none;
    background: {COLORS["card_bg"]};
    outline: none;
}}

QListWidget#reason_list::item {{
    padding: 10px 12px;
    border-left: 3px solid transparent;
    border-bottom: 1px solid {COLORS["border_decorative"]};
    min-height: 38px;
    font-size: 13px;
}}

QListWidget#reason_list::item:selected {{
    background-color: {COLORS["selection_bg"]};
    border-left: 3px solid {COLORS["selection_border"]};
    color: {COLORS["foreground"]};
    font-weight: 500;
}}

QListWidget#reason_list::item:hover:!selected {{
    background-color: #F8FAFC;
}}

QPushButton#btn_anmelden {{
    background-color: {COLORS["primary"]};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    min-height: 44px;
    padding: 0 16px;
}}

QPushButton#btn_anmelden:hover {{
    background-color: {COLORS["primary_hover"]};
}}

QPushButton#btn_anmelden:disabled {{
    background-color: {COLORS["primary"]};
    opacity: 0.38;
    color: #FFFFFF;
}}

QPushButton#btn_abmelden {{
    background-color: transparent;
    color: {COLORS["destructive"]};
    border: 1px solid {COLORS["destructive"]};
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    min-height: 44px;
    padding: 0 16px;
}}

QPushButton#btn_abmelden:hover {{
    background-color: #FEF2F2;
}}

QTableWidget#recent_table {{
    border: none;
    background: {COLORS["card_bg"]};
    gridline-color: {COLORS["border_decorative"]};
    font-size: 13px;
    outline: none;
}}

QTableWidget#recent_table QHeaderView::section {{
    background-color: {COLORS["card_bg"]};
    color: {COLORS["foreground"]};
    font-size: 13px;
    font-weight: 600;
    border-bottom: 1px solid {COLORS["border_ui"]};
    padding: 6px 8px;
}}

QScrollBar:vertical {{
    width: 6px;
    background: transparent;
}}

QScrollBar::handle:vertical {{
    background: {COLORS["border_ui"]};
    border-radius: 3px;
    min-height: 24px;
}}
"""
