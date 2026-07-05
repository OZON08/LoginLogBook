"""Platform dispatcher: routes fullscreen, lock, unlock, logoff, and user/host queries to OS-specific impl."""
import sys

from PyQt6.QtWidgets import QMainWindow


def _detect_platform() -> str:
    if sys.platform == "win32":
        return "win32"
    if sys.platform.startswith("linux"):
        return "linux"
    return "other"


def logoff() -> None:
    plat = _detect_platform()
    if plat == "win32":
        import app.platform_win32 as _w32
        _w32.logoff()
    elif plat == "linux":
        import app.platform_linux as _lnx
        _lnx.logoff()
    else:
        raise RuntimeError("logoff not supported on this platform")


def get_current_user() -> str:
    plat = _detect_platform()
    if plat == "win32":
        import app.platform_win32 as _w32
        return _w32.get_current_user()
    if plat == "linux":
        import app.platform_linux as _lnx
        return _lnx.get_current_user()
    return ""


def get_hostname() -> str:
    plat = _detect_platform()
    if plat == "win32":
        import app.platform_win32 as _w32
        return _w32.get_hostname()
    if plat == "linux":
        import app.platform_linux as _lnx
        return _lnx.get_hostname()
    import socket
    return socket.gethostname()


def setup_fullscreen(window: QMainWindow) -> None:
    window.showFullScreen()
    plat = _detect_platform()
    if plat == "win32":
        import app.platform_win32 as _w32
        _w32.setup_fullscreen(int(window.winId()))
    elif plat == "linux":
        import app.platform_linux as _lnx
        _lnx.setup_fullscreen(window)


def lock_system(window: QMainWindow) -> None:
    plat = _detect_platform()
    if plat == "win32":
        import app.platform_win32 as _w32
        _w32.lock(int(window.winId()))
    elif plat == "linux":
        import app.platform_linux as _lnx
        _lnx.lock(window)


def unlock_system(window: QMainWindow) -> None:
    plat = _detect_platform()
    if plat == "win32":
        import app.platform_win32 as _w32
        _w32.unlock(int(window.winId()))
    elif plat == "linux":
        import app.platform_linux as _lnx
        _lnx.unlock(window)
