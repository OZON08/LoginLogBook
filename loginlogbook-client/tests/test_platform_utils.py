"""Tests for platform detection and platform utility functions."""
import socket
import sys
from unittest.mock import MagicMock, patch

import pytest

import app.platform_utils as pu


def test_detect_returns_win32_or_linux():
    plat = pu._detect_platform()
    assert plat in ("win32", "linux", "other")


def test_detect_matches_sys_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert pu._detect_platform() == "win32"

    monkeypatch.setattr(sys, "platform", "linux")
    assert pu._detect_platform() == "linux"

    monkeypatch.setattr(sys, "platform", "darwin")
    assert pu._detect_platform() == "other"


def test_logoff_linux_calls_loginctl(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_SESSION_ID", "42")

    import app.platform_linux as _lnx
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)

    monkeypatch.setattr(_lnx.subprocess, "run", fake_run)
    pu.logoff()

    assert calls[0] == ["loginctl", "terminate-session", "42"]


def test_logoff_linux_falls_back_to_pkill(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_SESSION_ID", "")
    monkeypatch.setenv("USER", "testuser")

    import app.platform_linux as _lnx
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "loginctl":
            raise FileNotFoundError

    monkeypatch.setattr(_lnx.subprocess, "run", fake_run)
    pu.logoff()

    pkill_call = next(c for c in calls if c[0] == "pkill")
    assert pkill_call == ["pkill", "-KILL", "-u", "testuser"]


def test_logoff_win32_calls_exit_windows_ex(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    fake_user32 = MagicMock()
    fake_windll = MagicMock(user32=fake_user32)

    with patch("ctypes.windll", fake_windll, create=True):
        pu.logoff()

    fake_user32.ExitWindowsEx.assert_called_once_with(0, 0)


def test_logoff_other_raises(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")

    with pytest.raises(RuntimeError):
        pu.logoff()


def test_get_current_user_linux_from_env(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("USER", "alice")

    assert pu.get_current_user() == "alice"


def test_get_current_user_linux_fallback_to_pwd(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("USER", raising=False)

    import app.platform_linux as _lnx
    fake_entry = MagicMock(pw_name="bob")
    monkeypatch.setattr(_lnx.pwd, "getpwuid", lambda uid: fake_entry)

    assert pu.get_current_user() == "bob"


def test_get_current_user_win32_from_env(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("USERNAME", "winuser")

    assert pu.get_current_user() == "winuser"


def test_get_hostname_returns_string(monkeypatch):
    import app.platform_linux as _lnx
    monkeypatch.setattr(_lnx.socket, "gethostname", lambda: "myhost")
    monkeypatch.setattr(sys, "platform", "linux")

    assert pu.get_hostname() == "myhost"


def test_get_hostname_win32_returns_string(monkeypatch):
    import app.platform_win32 as _w32
    monkeypatch.setattr(_w32.socket, "gethostname", lambda: "winhost")
    monkeypatch.setattr(sys, "platform", "win32")

    assert pu.get_hostname() == "winhost"
