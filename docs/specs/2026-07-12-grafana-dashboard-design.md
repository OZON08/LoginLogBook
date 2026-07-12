# Grafana Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provisioned Grafana dashboard to the LoginLogBook stack that visualizes login/logout events from InfluxDB for both IT operations and security audiences.

**Architecture:** Grafana runs as a container in `docker-compose.yml`, on the existing `internal` network. It is proxied by nginx under `/grafana`. The InfluxDB datasource and dashboard are provisioned via config files committed to the repo — no manual setup required after `docker compose up`.

**Tech Stack:** Grafana 11 (OSS), InfluxDB 2.7 (Flux queries), nginx reverse proxy, Docker Compose.

## Global Constraints

- Grafana version: 11.x (OSS, no enterprise features)
- InfluxDB query language: Flux only (not InfluxQL)
- InfluxDB bucket: `logins`, org: `loginlogbook`, measurement: `login_events`
- Tags available: `host`, `os_user`, `event_type` (login|logout), `reason` (login only)
- Field: `count` (always 1)
- No code changes to the API or client
- Default time range: last 24 hours
- Grafana admin credentials via `.env` variables: `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`
- Grafana served at `https://<domain>/grafana` via nginx subpath proxy

---

## File Structure

**New files:**
- `loginlogbook-api/grafana/provisioning/datasources/influxdb.yaml` — InfluxDB Flux datasource
- `loginlogbook-api/grafana/provisioning/dashboards/dashboards.yaml` — dashboard provider
- `loginlogbook-api/grafana/dashboards/loginlogbook.json` — dashboard JSON
- `loginlogbook-api/grafana/grafana.ini` — Grafana config (subpath, anonymous disabled)

**Modified files:**
- `loginlogbook-api/docker-compose.yml` — add `grafana` service + volume
- `loginlogbook-api/nginx/nginx.conf` — add `/grafana` proxy location block
- `.env.example` — add `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`

---

## Dashboard Design

### Variables

| Variable | Source | Default |
|---|---|---|
| `$host` | Tag values of `host` in `login_events` | All |
| `$user` | Tag values of `os_user` in `login_events` | All |

Both are multi-value, with "All" option enabled.

### Row 1 — Betriebsübersicht

| Panel | Type | Flux Query Summary |
|---|---|---|
| Logins gesamt | Stat | Count of `event_type == "login"` in range |
| Aktive Clients | Stat | Distinct `host` tag values in range |
| Aktive Benutzer | Stat | Distinct `os_user` tag values in range |
| Anmeldungen über Zeit | Time Series | Login events aggregated per `$__interval` |
| Top-Clients (Top 10) | Bar Chart | Login count grouped by `host`, sorted desc, limit 10 |
| Anmeldegründe | Pie Chart | Login count grouped by `reason` tag |

### Row 2 — Sicherheit

| Panel | Type | Flux Query Summary |
|---|---|---|
| Anmeldungen nach Tageszeit | Heatmap | Events bucketed by hour-of-day vs weekday |
| Logins ohne Grund | Stat + Table | Login events where `reason` tag is absent |
| Login vs. Logout | Time Series | Both event types overlaid per `$__interval` |
| Außerhalb Geschäftszeiten | Stat | Logins where local hour < 7 or > 19 |

All panels respect `$host` and `$user` variable filters.

---

## Service Configuration

### Grafana service in docker-compose.yml

```yaml
grafana:
  image: grafana/grafana:11
  restart: unless-stopped
  depends_on:
    - influxdb
  environment:
    GF_SERVER_ROOT_URL: "%(protocol)s://%(domain)s/grafana"
    GF_SERVER_SERVE_FROM_SUB_PATH: "true"
    GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER}
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
    GF_AUTH_ANONYMOUS_ENABLED: "false"
  volumes:
    - grafana-data:/var/lib/grafana
    - ./grafana/provisioning:/etc/grafana/provisioning:ro
    - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
  networks:
    - internal
```

Add `grafana-data` to the top-level `volumes` block.

### nginx `/grafana` proxy block

```nginx
location /grafana/ {
    proxy_pass http://grafana:3000/grafana/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### grafana/provisioning/datasources/influxdb.yaml

```yaml
apiVersion: 1
datasources:
  - name: InfluxDB
    type: influxdb
    access: proxy
    url: http://influxdb:8086
    jsonData:
      version: Flux
      organization: loginlogbook
      defaultBucket: logins
    secureJsonData:
      token: ${INFLUX_TOKEN}
    isDefault: true
```

### grafana/provisioning/dashboards/dashboards.yaml

```yaml
apiVersion: 1
providers:
  - name: LoginLogBook
    folder: LoginLogBook
    type: file
    disableDeletion: true
    updateIntervalSeconds: 60
    options:
      path: /var/lib/grafana/dashboards
```

---

## Flux Query Examples

**Logins gesamt:**
```flux
from(bucket: "logins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "login_events"
      and r.event_type == "login"
      and (v.host == "All" or r.host == v.host)
      and (v.user == "All" or r.os_user == v.user))
  |> count()
```

**Top-Clients:**
```flux
from(bucket: "logins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "login_events" and r.event_type == "login")
  |> group(columns: ["host"])
  |> count()
  |> group()
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 10)
```

**Logins ohne Grund:**
```flux
from(bucket: "logins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "login_events"
      and r.event_type == "login"
      and not exists r.reason)
  |> count()
```

**Außerhalb Geschäftszeiten (< 7:00 oder > 19:00):**
```flux
import "date"
from(bucket: "logins")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "login_events" and r.event_type == "login")
  |> map(fn: (r) => ({r with hour: date.hour(t: r._time)}))
  |> filter(fn: (r) => r.hour < 7 or r.hour > 19)
  |> count()
```

---

## .env additions

```
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=changeme
```
