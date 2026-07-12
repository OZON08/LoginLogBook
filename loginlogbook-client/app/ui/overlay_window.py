"""Main fullscreen overlay window — wires all widgets and handles data flow."""
import getpass
import socket
from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from app.api_client import ApiClient
from app.cache import CacheStore
from app.config import Settings
from app.event_queue import EventQueue
from app.models import AppConfig, BrandingConfig, EventIn, EventOut, Reason
from app.ui.card_widget import CardWidget
from app.ui.confirm_dialog import ConfirmDialog
from app.ui.styles import COLORS, STYLESHEET


class _DataLoader(QThread):
    """Background thread: loads logo, reasons, config, and recent events from API."""

    reasons_loaded = pyqtSignal(list)        # list[Reason]
    logo_loaded = pyqtSignal(bytes, str)     # data, content_type
    config_loaded = pyqtSignal(object)       # AppConfig
    branding_loaded = pyqtSignal(object)     # BrandingConfig
    events_loaded = pyqtSignal(list)         # list[EventOut]
    finished_online = pyqtSignal()
    finished_offline = pyqtSignal()

    def __init__(self, client: ApiClient, host: str, days: int) -> None:
        super().__init__()
        self._client = client
        self._host = host
        self._days = days

    def run(self) -> None:
        online = True
        try:
            reasons = self._client.get_reasons()
            self.reasons_loaded.emit(reasons)
        except Exception:
            online = False

        try:
            logo_data, logo_ct = self._client.get_logo()
            self.logo_loaded.emit(logo_data, logo_ct)
        except Exception:
            pass

        try:
            cfg = self._client.get_config()
            self.config_loaded.emit(cfg)
        except Exception:
            pass

        try:
            branding = self._client.get_branding_config()
            self.branding_loaded.emit(branding)
        except Exception:
            pass

        try:
            events = self._client.get_recent_events(self._host, self._days)
            self.events_loaded.emit(events)
        except Exception:
            pass

        if online:
            self.finished_online.emit()
        else:
            self.finished_offline.emit()


class OverlayWindow(QMainWindow):
    login_completed = pyqtSignal()

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._cache = CacheStore(settings.cache_dir)
        self._queue = EventQueue(settings.queue_file)
        self._client = ApiClient(settings)
        self._host = socket.gethostname()
        self._os_user = getpass.getuser()
        self._recent_days = 7
        self._loader: _DataLoader | None = None
        self._logo_data: tuple[bytes, str] | None = None
        self._logo_height: int = 120

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(STYLESHEET)

        # Dark overlay container — fills the whole window
        self._container = QWidget()
        container = self._container
        container.setStyleSheet(f"background-color: {COLORS['overlay_bg']};")
        self.setCentralWidget(container)

        # Card centered via layout
        self._card = CardWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()
        inner = QHBoxLayout()
        inner.addStretch()
        inner.addWidget(self._card)
        inner.addStretch()
        outer.addLayout(inner)
        outer.addStretch()

        self._card.footer.set_user_host(self._os_user, self._host)

        self._card.search.filter_changed.connect(self._card.reason_list.apply_filter)
        self._card.reason_list.selection_changed.connect(self._on_list_selection)
        self._card.free_text.textChanged.connect(self._on_free_text_changed)
        self._card.button_row.anmelden_clicked.connect(self._on_anmelden)
        self._card.button_row.abmelden_clicked.connect(self._on_abmelden)

        self._populate_from_cache()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._start_loading()

    def _populate_from_cache(self) -> None:
        if reasons := self._cache.load_reasons():
            self._card.reason_list.populate(reasons)
            self._card.logo.set_loading(False)
        if logo := self._cache.load_logo():
            self._card.logo.set_logo(*logo)
        if cfg := self._cache.load_config():
            self._recent_days = cfg.recent_days
        if events := self._cache.load_recent_events():
            self._card.recent_table.populate(events, self._recent_days)
        self._card.footer.set_status(online=False)
        self._card.search.set_focus()

    def _start_loading(self) -> None:
        if self._loader is not None and self._loader.isRunning():
            self._loader.quit()
            self._loader.wait()
        self._loader = _DataLoader(self._client, self._host, self._recent_days)
        self._loader.reasons_loaded.connect(self._on_reasons)
        self._loader.logo_loaded.connect(self._on_logo)
        self._loader.config_loaded.connect(self._on_config)
        self._loader.branding_loaded.connect(self._on_branding)
        self._loader.events_loaded.connect(self._on_events)
        self._loader.finished_online.connect(
            lambda: self._card.footer.set_status(online=True)
        )
        self._loader.finished_offline.connect(
            lambda: self._card.footer.set_status(online=False)
        )
        self._loader.start()

    def _on_list_selection(self, reason: Reason | None) -> None:
        if not self._card.free_text.text().strip():
            self._card.button_row.set_selected_reason(reason)

    def _on_free_text_changed(self, text: str) -> None:
        stripped = text.strip()
        if stripped:
            self._card.button_row.set_selected_reason(
                Reason(id="", label=stripped, active=True)
            )
        else:
            self._card.button_row.set_selected_reason(
                self._card.reason_list.selected_reason()
            )

    def _on_reasons(self, reasons: list[Reason]) -> None:
        self._card.reason_list.populate(reasons)
        self._cache.save_reasons(reasons)

    def _on_logo(self, data: bytes, content_type: str) -> None:
        self._logo_data = (data, content_type)
        self._card.logo.set_logo(data, content_type, self._logo_height)
        self._cache.save_logo(data, content_type)

    def _on_branding(self, cfg: BrandingConfig) -> None:
        self._logo_height = cfg.logo_height
        self._card.logo.set_background(cfg.logo_bg)
        if self._logo_data:
            self._card.logo.set_logo(*self._logo_data, cfg.logo_height)

    def _on_config(self, cfg: AppConfig) -> None:
        self._recent_days = cfg.recent_days
        self._card.free_text.setVisible(cfg.allow_free_text)
        self._card.or_label.setVisible(cfg.allow_free_text)
        if not cfg.allow_free_text:
            self._card.free_text.clear()
        self._cache.save_config(cfg)

    def _on_events(self, events: list[EventOut]) -> None:
        self._card.recent_table.populate(events, self._recent_days)
        self._cache.save_recent_events(events)

    def _on_anmelden(self, reason: Reason) -> None:
        self._card.button_row.set_loading(True)
        event = EventIn(
            event_type="login",
            host=self._host,
            os_user=self._os_user,
            reason=reason.label,
            timestamp=datetime.now(timezone.utc),
        )
        try:
            self._client.post_event(event)
        except Exception:
            self._queue.enqueue(event)
        try:
            self._queue.flush(self._client.post_event)
        except Exception:
            pass
        self.login_completed.emit()
        self.close()

    def _on_abmelden(self) -> None:
        dialog = ConfirmDialog(self)
        if dialog.exec() == ConfirmDialog.DialogCode.Accepted:
            try:
                import app.platform_utils as pu  # noqa: PLC0415
                pu.logoff()
            except ImportError:
                pass
