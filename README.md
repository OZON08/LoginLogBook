# LoginLogBook

Fullscreen login overlay for Windows and Linux — records why users log into servers before releasing the desktop.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-green)](https://pypi.org/project/PyQt6/)

## What it does

When a user logs into a server, LoginLogBook displays a fullscreen overlay that blocks the desktop until a login reason is selected. The reason is recorded along with timestamp, hostname, and OS user. The overlay disappears only after a reason is confirmed.

On logout, the user can optionally confirm via a dialog before the session is terminated.

## Architecture

```
PyQt6 Client  ──HTTPS──►  ┌─ nginx (TLS) ─┐
(per host)                │   /       ──►  FastAPI (loginlogbook-api) ──► InfluxDB
                          │   /admin  ──►  Admin web UI (served by the API)
                          │   /grafana──►  Grafana (dashboards)        ──► InfluxDB
                          └───────────────┘
```

- **Client** — fullscreen PyQt6 overlay, runs on each managed host
- **API** — FastAPI backend, authenticated with per-host tokens; also serves the admin web UI
- **Admin UI** — browser UI at `/admin` for managing client tokens, login reasons, branding (logo/colours) and the interface language
- **Grafana** — provisioned dashboards at `/grafana` (Betrieb, Sicherheit, Protokoll) reading login events from InfluxDB
- **InfluxDB** — time-series storage for login events (not exposed externally)
- **nginx** — TLS termination, HTTP→HTTPS redirect, security headers, reverse proxy for the API and Grafana

## Requirements

- Python 3.12+
- PyQt6 6.7+
- Network access to the LoginLogBook API

## Installation

### From source

```bash
git clone https://github.com/OZON08/LoginLogBook.git
cd LoginLogBook/loginlogbook-client
pip install .
```

### Linux extras (X11 fullscreen lock)

```bash
pip install ".[linux]"
```

### Build a standalone binary

```bash
pip install ".[package]"
pyinstaller loginlogbook-client.spec
# → dist/loginlogbook-client
```

## Configuration

All settings are environment variables:

| Variable | Required | Description |
|---|---|---|
| `API_URL` | yes | Base URL of the LoginLogBook API, e.g. `https://llb.example.com` |
| `CLIENT_TOKEN` | yes | Per-host authentication token |
| `API_CA_BUNDLE` | no | Path to CA certificate bundle for self-signed certs |
| `CACHE_DIR` | no | Local cache directory (default: `~/.loginlogbook/cache`) |
| `QUEUE_FILE` | no | Offline queue file (default: `~/.loginlogbook/queue.json`) |

Example `/etc/loginlogbook.env`:

```env
API_URL=https://llb.example.com
CLIENT_TOKEN=your-unique-host-token
API_CA_BUNDLE=/etc/ssl/certs/internal-ca.crt
```

Client tokens are issued and revoked in the admin UI (see below); each host gets its own.

## Autostart (Linux)

Copy the desktop file to the system autostart directory:

```bash
cp autostart/loginlogbook-client.desktop /etc/xdg/autostart/
```

Or for a single user:

```bash
cp autostart/loginlogbook-client.desktop ~/.config/autostart/
```

## Admin UI

A browser interface at `https://llb.example.com/admin` (admin-token protected) manages:

- **Clients** — create and revoke per-host client tokens
- **Reasons** — the selectable login reasons shown in the overlay
- **Branding** — upload a logo and set its size and background colour
- **Language** — switch the interface language (see below)

The admin token is sent via the `X-Admin-Token` header and is never stored in the browser's `localStorage`.

## Dashboards (Grafana)

Grafana is provisioned automatically and reachable at `https://llb.example.com/grafana`. Three dashboards visualise the login events:

- **Betrieb** — totals, active clients/users, logins over time, top clients, login reasons
- **Sicherheit** — logins by hour of day, out-of-hours logins (outside 07–17), logins without a reason, login vs. logout
- **Protokoll** — a filterable table of every login/logout event

The InfluxDB datasource and dashboards are provisioned from files; no manual setup is needed after `docker compose up`.

## Languages (i18n)

The interface ships in **German (default)** and **English**. The active language is a server-side setting, switched in the admin UI, and applies to the client, admin UI and API. Fixed UI texts live in JSON locale files; adding a language means copying `de.json` to `xx.json` per component and translating it — it then appears automatically in the admin language switcher.

The Grafana dashboards (titles, labels, tooltips) are also translated, but at build time: run `uv run python -m scripts.build_dashboards --lang <code>` and restart Grafana. See `CLAUDE.md` for the full procedure.

## Offline behaviour

If the API is unreachable, the client:
1. Populates the UI from the local cache (reasons, recent events, logo)
2. Queues submitted login events to disk
3. Flushes the queue on the next successful connection

## Accessibility

The client targets **BITV 2.0** (= WCAG 2.1 AA + EN 301 549), as required by Rheinland-Pfalz regulations for public-sector software. All interactive elements carry accessible names, contrast ratios meet 4.5:1 minimum, and font sizes are 12 px minimum.

## Development

The repository uses [uv](https://docs.astral.sh/uv/). Each component has its own environment:

```bash
# Client (PyQt6)
cd loginlogbook-client
uv run pytest        # 57 tests, run headless (pytest-qt, no display needed)

# API (FastAPI)
cd loginlogbook-api
uv run pytest        # 82 tests
```

Regenerate the Grafana dashboards after changing their templates or locales:

```bash
cd loginlogbook-api
uv run python -m scripts.build_dashboards --lang de
```

## Support

If LoginLogBook saves you time:

- [GitHub Sponsors](https://github.com/sponsors/OZON08)
- [Buy Me a Coffee](https://www.buymeacoffee.com/ozon)

## License

[MIT](LICENSE) — © 2026 OZON08
