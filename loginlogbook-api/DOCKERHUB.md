# LoginLogBook API

Fullscreen login overlay for Windows and Linux — records why users log into servers before releasing the desktop.

## What it does

When a user logs into a server, the LoginLogBook client displays a fullscreen overlay that blocks the desktop until a login reason is selected. The reason is recorded along with timestamp, hostname, and OS user.

This image is the **API backend**: a FastAPI service that stores login events in InfluxDB and serves reasons, branding, and client configuration.

```
PyQt6 Client  ──HTTPS──►  loginlogbook-api  ──►  InfluxDB
(per host)                       │
                              nginx (TLS)
```

## Quick start

```bash
# 1. Clone the repo (for docker-compose.yml and nginx config)
git clone https://github.com/OZON08/LoginLogBook.git
cd LoginLogBook/loginlogbook-api

# 2. Create your .env from the example and fill in the values
cp .env.example .env

# 3. Start
docker compose up -d
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `INFLUX_URL` | yes | InfluxDB URL, e.g. `http://influxdb:8086` |
| `INFLUX_TOKEN` | yes | InfluxDB admin token |
| `INFLUX_ORG` | yes | InfluxDB organisation name |
| `INFLUX_BUCKET` | yes | InfluxDB bucket name |
| `ADMIN_TOKEN` | yes | Token for admin endpoints (`/clients`, `/reasons`) |
| `CLIENT_TOKEN` | yes | Token accepted from client hosts |
| `REASONS_FILE` | no | Path to reasons JSON (default: `/data/reasons.json`) |
| `LOGO_DIR` | no | Path to logo directory (default: `/data/logo`) |
| `CLIENTS_FILE` | no | Path to client store JSON (default: `/data/clients.json`) |

## Tags

| Tag | Description |
|---|---|
| `latest` | Latest stable release |
| `v1`, `v1.0`, `v1.0.0` | Pinned release versions |
| `dev` | Built from the latest commit on `main` |

## Links

- [GitHub](https://github.com/OZON08/LoginLogBook)
- [License: MIT](https://github.com/OZON08/LoginLogBook/blob/main/LICENSE)
