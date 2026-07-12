"""Application entry point."""
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app.config import get_settings
from app.ui.overlay_window import OverlayWindow
from app.ui.styles import STYLESHEET

_ICON = Path(__file__).parent / "resources" / "icon.png"


def main() -> None:
    if os.environ.get("WAYLAND_DISPLAY") and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "wayland"

    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)

    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Language.German, QLocale.Country.Germany))
    app.setApplicationName("LoginLogBook")
    if _ICON.exists():
        app.setWindowIcon(QIcon(str(_ICON)))
    app.setStyleSheet(STYLESHEET)

    settings = get_settings()
    window = OverlayWindow(settings)

    try:
        import app.platform_utils as platform_utils  # noqa: PLC0415
        window._card.footer.set_user_host(
            platform_utils.get_current_user(),
            platform_utils.get_hostname(),
        )
    except ImportError:
        pass

    window.login_completed.connect(app.quit)
    window.showFullScreen()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
