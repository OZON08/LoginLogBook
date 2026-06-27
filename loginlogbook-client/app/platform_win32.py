"""Windows-specific: HWND_TOPMOST, DisableTaskMgr, and logoff via ctypes."""
import ctypes
import os
import socket

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
_REG_KEY = "DisableTaskMgr"


def setup_fullscreen(hwnd: int) -> None:
    ctypes.windll.user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
    )


def lock(hwnd: int) -> None:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, _REG_KEY, 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except OSError:
        pass


def unlock(hwnd: int) -> None:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, _REG_KEY)
        winreg.CloseKey(key)
    except OSError:
        pass


def logoff() -> None:
    ctypes.windll.user32.ExitWindowsEx(0, 0)


def get_current_user() -> str:
    return os.getenv("USERNAME") or ""


def get_hostname() -> str:
    return socket.gethostname()
