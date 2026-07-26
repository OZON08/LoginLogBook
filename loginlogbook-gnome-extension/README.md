# LoginLogBook GNOME Shell extension

Enforces the LoginLogBook login-reason prompt at **GNOME/Wayland** session start
with a real compositor-level input grab (`Main.pushModal`) and full UI parity
with the PyQt overlay. Under Wayland an application window cannot grab global
input — only a shell extension can — so desktop enforcement lives here, while
the PyQt client remains the overlay for X11 and Windows.

- **GNOME Shell 50** (gjs 1.88, ESM). `metadata.json` targets `shell-version: ["50"]`.
- UUID: `loginlogbook@ozon08.github.io`.
- No npm / external runtime deps — only `gi://` typelibs (`GObject`, `Gio`,
  `GLib`, `Soup` 3.0, `St`, `Clutter`, `Shell`, `Meta`) plus dconf for the
  enforced install.

## Configuration

Reads the **same** `/etc/loginlogbook.env` as the PyQt client:

| Variable        | Meaning                        | Default                          |
|-----------------|--------------------------------|----------------------------------|
| `API_URL`       | Base URL of loginlogbook-api   | *(required — else fail-open)*    |
| `CLIENT_TOKEN`  | `X-Client-Token` header value  | *(empty)*                        |
| `API_CA_BUNDLE` | CA bundle for TLS verification | *(system default)*               |
| `CACHE_DIR`     | Cache directory                | `~/.loginlogbook/cache`          |
| `QUEUE_FILE`    | Offline event queue            | `~/.loginlogbook/queue.json`     |

## Fail-open safety

Any config error, missing `API_URL`, failed modal grab, or unexpected
`enable()` exception results in **no grab** — the event is logged to the journal
and the user reaches the desktop normally. The extension never locks a user out.

## Residual gap

The `pushModal` grab blocks Super, Alt+Tab, Activities/Overview, and
workspace-switch shortcuts. It does **not** block VT switching
(`Ctrl+Alt+F1…F7`) or the hardware power button — those are handled by the
kernel / logind, below the compositor, and cannot be intercepted by an
extension. This matches the enforcement ceiling of any in-session mechanism.

## Unit tests

Headless, pure-gjs (no jasmine/npm):

```bash
gjs -m tests/run.js
```

Covers config, models, store (cache + offline queue), the API client (mock
transport — Soup never loaded), i18n + locale key parity, the ModalGuard state
machine + monitor geometry, and the pure UI helpers. The `St`/`Shell`
integration (grab, widgets, orchestration) is verified via the manual smoke
checklist below, since it needs a live GNOME session.

## Install (enforced, system-wide)

```bash
sudo packaging/install.sh      # copies to /usr/share/…, force-enables via dconf
```

Users must re-login to apply (Wayland cannot live-reload the shell).
`DESTDIR=…` stages a dry-run install without touching dconf.
Uninstall with `sudo packaging/uninstall.sh`.

For local development you can symlink instead:

```bash
ln -sfn "$PWD" ~/.local/share/gnome-shell/extensions/loginlogbook@ozon08.github.io
gnome-extensions enable loginlogbook@ozon08.github.io
# then log out and back in
```

## Manual smoke checklist

Run once on a live GNOME/Wayland session with `/etc/loginlogbook.env` present
and the API reachable. Record the outcome.

| # | Check | Result |
|---|-------|--------|
| 1 | After login the overlay covers **all** monitors | |
| 2 | Super, Alt+Tab, Activities/Overview, workspace-switch are blocked | |
| 3 | With API stopped (`docker compose stop api`) and re-login: cached reasons/logo shown, footer offline; picking a reason still closes the overlay and the event lands in the queue file | |
| 4 | With API up, pick a reason → overlay releases, desktop free, event appears in InfluxDB/Grafana | |
| 5 | Click *Abmelden ohne Anmeldungsgrund* → confirm → session terminates | |
| 6 | Rename `/etc/loginlogbook.env` away → login → **no grab**, desktop immediately usable (fail-open); `journalctl --user -b -g loginlogbook` shows the fail-open line | |
| 7 | `journalctl --user -b -g loginlogbook` shows no unhandled exceptions | |
