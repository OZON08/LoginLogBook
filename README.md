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
PyQt6 Client  ──HTTPS──►  FastAPI (loginlogbook-api)  ──►  InfluxDB
(per host)                  │
                            └── nginx (TLS termination)
```

- **Client** — fullscreen PyQt6 overlay, runs on each managed host
- **API** — FastAPI backend, authenticated with per-host tokens
- **InfluxDB** — time-series storage for login events (not exposed externally)
- **nginx** — TLS termination, HTTP→HTTPS redirect, security headers

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

## Autostart (Linux)

Copy the desktop file to the system autostart directory:

```bash
cp autostart/loginlogbook-client.desktop /etc/xdg/autostart/
```

Or for a single user:

```bash
cp autostart/loginlogbook-client.desktop ~/.config/autostart/
```

## Offline behaviour

If the API is unreachable, the client:
1. Populates the UI from the local cache (reasons, recent events, logo)
2. Queues submitted login events to disk
3. Flushes the queue on the next successful connection

## Accessibility

The client targets **BITV 2.0** (= WCAG 2.1 AA + EN 301 549), as required by Rheinland-Pfalz regulations for public-sector software. All interactive elements carry accessible names, contrast ratios meet 4.5:1 minimum, and font sizes are 12 px minimum.

## Development

```bash
cd loginlogbook-client
pip install ".[dev]"
pytest
```

All 51 tests run without a display (headless pytest-qt).

## Support

If LoginLogBook saves you time:

- [GitHub Sponsors](https://github.com/sponsors/OZON08)
- [Buy Me a Coffee](https://www.buymeacoffee.com/ozon)

## License

[MIT](LICENSE) — © 2026 OZON08
