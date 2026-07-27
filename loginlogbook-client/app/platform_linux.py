"""Linux-specific: keyboard grab via python-xlib, and logoff via loginctl."""
import os
import pwd
import socket
import subprocess

_display = None
_grabbed = False


def _get_display():
    global _display
    if _display is None:
        try:
            from Xlib import display as xdisplay
            _display = xdisplay.Display()
        except Exception:
            _display = None
    return _display


def logoff() -> None:
    session_id = os.getenv("XDG_SESSION_ID", "")
    try:
        if session_id:
            subprocess.run(["loginctl", "terminate-session", session_id], check=False)
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        user = os.getenv("USER", "")
        subprocess.run(["pkill", "-KILL", "-u", user], check=False)


def get_current_user() -> str:
    return os.getenv("USER") or pwd.getpwuid(os.getuid()).pw_name


def get_hostname() -> str:
    return socket.gethostname()


def setup_fullscreen(window) -> None:
    # No-op: input confinement on Wayland is handled by the GNOME Shell
    # extension (loginlogbook-gnome-extension), not by the Qt client.
    # On X11 the keyboard grab in lock() applies (see task #18).
    return


def lock(window) -> None:
    global _grabbed
    d = _get_display()
    if d is None:
        return
    try:
        from Xlib import X
        root = d.screen().root
        root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)
        d.flush()
        _grabbed = True
    except Exception:
        pass


def unlock(window) -> None:
    global _grabbed
    if not _grabbed:
        return
    d = _get_display()
    if d is None:
        return
    try:
        from Xlib import X
        d.ungrab_keyboard(X.CurrentTime)
        d.flush()
        _grabbed = False
    except Exception:
        pass
