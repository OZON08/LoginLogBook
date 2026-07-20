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

## Server deployment (loginlogbook-api)

The server side runs as a Docker Compose stack in `loginlogbook-api/`: nginx (TLS
termination + reverse proxy), the FastAPI API, InfluxDB (time-series storage),
Grafana (dashboards), a one-shot `certs-init` container, and an optional `certbot`
container. Only nginx is published to the host — on ports **80** (HTTP → HTTPS
redirect + ACME challenge) and **443** (HTTPS). Everything else talks over the
internal Docker network.

### First start

```bash
cd loginlogbook-api
cp .env.example .env          # then fill in the secrets (see the table below)
docker compose up -d          # brings up nginx, api, influxdb, grafana, certs-init
```

On the first `up`, InfluxDB bootstraps itself from the `DOCKER_INFLUXDB_INIT_*`
variables (org, bucket, admin user/password, admin token). **After the first
successful start, remove or comment out `DOCKER_INFLUXDB_INIT_MODE` in `.env`** —
it only drives the one-time setup and InfluxDB refuses to re-run it against an
initialised volume. The `INFLUX_TOKEN` the API and Grafana use must match
`DOCKER_INFLUXDB_INIT_ADMIN_TOKEN`.

`certs-init` generates a self-signed bootstrap certificate on first start so nginx
can serve HTTPS immediately (see [HTTPS & certificates](#https--certificates)).

Update the running stack after pulling new images:

```bash
docker compose pull && docker compose up -d
```

### Services

| Service | Image | Purpose | Published ports |
|---|---|---|---|
| `nginx` | `nginx:1.27-alpine` | TLS termination, HTTP→HTTPS redirect, reverse proxy, error pages, rate limiting | `80`, `443` |
| `api` | `ozon08/loginlogbook-api:latest` | FastAPI backend + admin UI | internal only |
| `influxdb` | `influxdb:2.7` | Login-event storage | internal only |
| `grafana` | `grafana/grafana:13.1.0` | Dashboards at `/grafana` | internal only |
| `certs-init` | `alpine/openssl:3.5.7` | One-shot self-signed bootstrap cert (never overwrites an existing one) | — |
| `certbot` | `certbot/certbot:v5.7.0` | Optional Let's Encrypt issuance + auto-renewal (profile `certbot`) | — |

### Server configuration

Server settings are environment variables, provided via `loginlogbook-api/.env`
(copied from `.env.example`). The API reads them through pydantic settings
(`app/config.py`); the `DOCKER_INFLUXDB_INIT_*` and `GRAFANA_*` variables are
consumed by the InfluxDB and Grafana containers respectively.

| Variable | Required | Description |
|---|---|---|
| `INFLUX_URL` | yes | InfluxDB base URL (default `http://influxdb:8086`) |
| `INFLUX_TOKEN` | yes | InfluxDB API token — must equal `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN` |
| `INFLUX_ORG` | yes | InfluxDB organisation (default `loginlogbook`) |
| `INFLUX_BUCKET` | yes | InfluxDB bucket for login events (default `logins`) |
| `ADMIN_TOKEN` | yes | Token for the admin UI and `/clients` / `/reasons` management endpoints (`X-Admin-Token` header) |
| `CLIENT_TOKEN` | yes | Client token accepted from login overlays (one shared token, or manage per-host tokens via the admin UI) |
| `REASONS_FILE` | no | Path inside the container for the reasons store (default `/data/reasons.json`) |
| `LOGO_DIR` | no | Directory for the uploaded branding logo (default `/data/logo`) |
| `CLIENTS_FILE` | no | Path for the per-host client-token store (default `/data/clients.json`) |
| `TLS_DOMAIN` | yes | Domain LoginLogBook is reachable under — CN of the self-signed cert, certbot domain, and Grafana root URL |
| `CERTBOT_EMAIL` | for certbot | E-mail for Let's Encrypt registration and expiry warnings |
| `DOCKER_INFLUXDB_INIT_MODE` | first start only | Set to `setup` for the first start; **remove afterwards** |
| `DOCKER_INFLUXDB_INIT_USERNAME` | first start only | InfluxDB admin username created on first start |
| `DOCKER_INFLUXDB_INIT_PASSWORD` | first start only | InfluxDB admin password created on first start |
| `DOCKER_INFLUXDB_INIT_ORG` | first start only | InfluxDB org created on first start (match `INFLUX_ORG`) |
| `DOCKER_INFLUXDB_INIT_BUCKET` | first start only | InfluxDB bucket created on first start (match `INFLUX_BUCKET`) |
| `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN` | first start only | Admin token created on first start (match `INFLUX_TOKEN`) |
| `GRAFANA_ADMIN_USER` | yes | Grafana admin username |
| `GRAFANA_ADMIN_PASSWORD` | yes | Grafana admin password |

Reasons, branding and language are also editable at runtime via the admin UI; the
`REASONS_FILE` / `LOGO_DIR` / `CLIENTS_FILE` paths point at the persisted
`api-data` volume so they survive restarts.

## HTTPS & certificates

LoginLogBook terminates TLS in nginx and always reads exactly one certificate
pair: `nginx/certs/server.crt` and `nginx/certs/server.key`. Whatever produces
those two files — the self-signed bootstrap or certbot — nginx never needs to
know.

### Default: self-signed (internal)

On the first `docker compose up -d`, the `certs-init` container generates a
self-signed certificate (CN = `TLS_DOMAIN`) if none exists yet. nginx serves
HTTPS with it immediately. Browsers show a certificate warning — expected and
fine for internal deployments. An existing certificate is never overwritten, so
certbot-issued certs are safe across restarts.

### Optional: Let's Encrypt (public domain)

Prerequisites: a public domain, DNS pointing at the host, ports 80/443 reachable.
Set `TLS_DOMAIN` and `CERTBOT_EMAIL` in `.env`, then:

```bash
docker compose --profile certbot up -d       # start the certbot service
./scripts/init-letsencrypt.sh                 # issue once (add --staging to test)
```

Issuance uses the HTTP-01 challenge served from `/.well-known/acme-challenge/`
(handled before the HTTPS redirect). The certbot container then renews
automatically (checks every 12 h, renews from 30 days before expiry) and copies
the renewed certificate into the nginx cert path via its deploy hook. nginx
reloads itself every 6 h to pick up renewed certificates without a restart.

### Manual smoke test

1. Fresh host, no certbot: `docker compose up -d` → `https://<host>` serves a
   page with a certificate warning (self-signed).
2. With a domain + certbot: after `init-letsencrypt.sh`, `https://$TLS_DOMAIN`
   serves a browser-trusted certificate without a warning.

## Error pages & rate limiting

nginx and the API return branded, localized error responses instead of raw
server errors.

- **Gateway errors (5xx).** If the API or Grafana is unavailable, nginx serves
  static branded pages for `502` / `503` / `504` from `nginx/errors/`. The page
  language follows the browser's `Accept-Language` header (`map $http_accept_language`),
  falling back to the default language.
- **API errors.** The API itself returns branded HTML for browser requests and
  structured JSON for programmatic clients, so the PyQt client and the admin UI
  both get machine-readable errors while humans get a readable page.
- **Rate limiting.** nginx caps requests at **60 req/min** per client
  (`limit_req_zone … rate=60r/m`). Over-limit requests receive a branded **429**
  page (`limit_req_status 429`) rather than nginx's default, again localized via
  `Accept-Language`.

## Languages (i18n)

The interface ships in **German (default)** and **English**. The active language is a server-side setting (`/data/settings.json`), switched in the admin UI, and applies to the client, admin UI and API. Fixed UI texts live in JSON locale files; key parity across languages is enforced by tests (`test_locale_parity.py`).

**Adding a language `xx`:**

1. Copy `de.json` to `xx.json` and translate it in each locale directory:
   - `loginlogbook-client/app/locales/`
   - `loginlogbook-api/app/locales/admin/`
   - `loginlogbook-api/app/locales/api/`
   - `loginlogbook-api/app/locales/grafana/`
2. Client, admin UI and API are done — `xx` appears automatically in the admin language switcher.
3. Grafana dashboards are translated at **build time** (they are static provisioned JSON, not switched live). Regenerate and restart:
   ```bash
   cd loginlogbook-api
   uv run python -m scripts.build_dashboards --lang xx
   docker compose restart grafana
   ```
   The generator fills the dashboard titles, panel labels, and description tooltips from `locales/grafana/xx.json`.

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
