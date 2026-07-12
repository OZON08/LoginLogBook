"""Design token colors and Qt stylesheet for the entire overlay."""

COLORS: dict[str, str] = {
    "overlay_bg": "rgba(15, 23, 42, 224)",
    "card_bg": "#1E293B",
    "primary": "#3B82F6",
    "primary_hover": "#2563EB",
    "foreground": "#F1F5F9",
    "muted": "#94A3B8",
    "border_decorative": "#334155",
    "border_ui": "#475569",
    "selection_bg": "#1D3461",
    "selection_border": "#3B82F6",
    "destructive": "#F87171",
    "status_online": "#4ADE80",
    "status_offline": "#FCD34D",
    "skeleton": "#334155",
    "skeleton_shine": "#475569",
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
    color: {COLORS["foreground"]};
    min-height: 44px;
}}

QLineEdit#search_field:focus {{
    border: 2px solid {COLORS["primary"]};
}}

QListWidget#reason_list {{
    border: none;
    background: {COLORS["card_bg"]};
    color: {COLORS["foreground"]};
    outline: none;
}}

QListWidget#reason_list::item {{
    padding: 10px 12px;
    border-left: 3px solid transparent;
    border-bottom: 1px solid {COLORS["border_decorative"]};
    min-height: 38px;
    font-size: 13px;
    color: {COLORS["foreground"]};
}}

QListWidget#reason_list::item:selected {{
    background-color: {COLORS["selection_bg"]};
    border-left: 3px solid {COLORS["selection_border"]};
    color: {COLORS["foreground"]};
    font-weight: 500;
}}

QListWidget#reason_list::item:hover:!selected {{
    background-color: #273549;
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
    background-color: rgba(248, 113, 113, 0.15);
}}

QTableWidget#recent_table {{
    border: none;
    background: {COLORS["card_bg"]};
    color: {COLORS["foreground"]};
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

QLineEdit#free_text_input {{
    border: 1px solid {COLORS["border_ui"]};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    background: {COLORS["card_bg"]};
    color: {COLORS["foreground"]};
    min-height: 40px;
}}

QLineEdit#free_text_input:focus {{
    border: 2px solid {COLORS["primary"]};
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
