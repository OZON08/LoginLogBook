# Grafana Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provisioned Grafana 11 dashboard to the LoginLogBook Docker Compose stack, visualizing login/logout events from InfluxDB for IT operations and security audiences, accessible at `/grafana` via nginx.

**Architecture:** Grafana runs as a container in `loginlogbook-api/docker-compose.yml` on the existing `internal` network. Config files committed to the repo are mounted read-only and provision the InfluxDB datasource and dashboard automatically on first start. nginx proxies `/grafana/` to the Grafana container on port 3000.

**Tech Stack:** Grafana 11 (OSS), InfluxDB 2.7 (Flux), nginx 1.27-alpine, Docker Compose.

## Global Constraints

- Grafana image: `grafana/grafana:11`
- InfluxDB query language: Flux only (not InfluxQL)
- InfluxDB bucket: `logins`, org: `loginlogbook`, measurement: `login_events`
- Tags: `host`, `os_user`, `event_type` (login|logout), `reason` (login only, optional)
- Field: `count` (always 1)
- No changes to API or client Python code
- Default dashboard time range: last 24 hours
- Grafana credentials via `.env`: `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`
- Grafana subpath: `/grafana` — `GF_SERVER_SERVE_FROM_SUB_PATH=true`
- All provisioning files mounted read-only; `disableDeletion: true` in dashboard provider

---

## File Structure

**Create:**
- `loginlogbook-api/grafana/provisioning/datasources/influxdb.yaml`
- `loginlogbook-api/grafana/provisioning/dashboards/dashboards.yaml`
- `loginlogbook-api/grafana/dashboards/loginlogbook.json`

**Modify:**
- `loginlogbook-api/docker-compose.yml` — add `grafana` service + `grafana-data` volume
- `loginlogbook-api/nginx/nginx.conf` — add `/grafana/` proxy location
- `loginlogbook-api/.env.example` — add `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`

---

## Task 1: Provisioning files + Compose + env

**Files:**
- Create: `loginlogbook-api/grafana/provisioning/datasources/influxdb.yaml`
- Create: `loginlogbook-api/grafana/provisioning/dashboards/dashboards.yaml`
- Modify: `loginlogbook-api/docker-compose.yml`
- Modify: `loginlogbook-api/.env.example`

**Interfaces:**
- Produces: running `grafana` container accessible at `http://grafana:3000` inside the `internal` network; datasource named `InfluxDB` wired to `http://influxdb:8086`

- [ ] **Step 1: Create the datasource provisioning file**

Create `loginlogbook-api/grafana/provisioning/datasources/influxdb.yaml`:

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
    editable: false
```

- [ ] **Step 2: Create the dashboard provider file**

Create `loginlogbook-api/grafana/provisioning/dashboards/dashboards.yaml`:

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

- [ ] **Step 3: Add the grafana service to docker-compose.yml**

Modify `loginlogbook-api/docker-compose.yml`. Add the `grafana` service after `api`, add `grafana-data` to the `volumes` block, and add `grafana` to the `nginx` depends_on:

```yaml
services:
  influxdb:
    image: influxdb:2.7
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "influx", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 20s
    env_file: .env
    volumes:
      - influx-data:/var/lib/influxdb2
    networks:
      - internal

  api:
    image: ozon08/loginlogbook-api:latest
    restart: unless-stopped
    depends_on:
      influxdb:
        condition: service_healthy
    env_file: .env
    volumes:
      - api-data:/data
    networks:
      - internal

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
      GF_USERS_ALLOW_SIGN_UP: "false"
      INFLUX_TOKEN: ${INFLUX_TOKEN}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    networks:
      - internal

  nginx:
    image: nginx:1.27-alpine
    restart: unless-stopped
    depends_on:
      - api
      - grafana
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    networks:
      - internal

networks:
  internal:

volumes:
  influx-data:
  api-data:
  grafana-data:
```

- [ ] **Step 4: Add Grafana credentials to .env.example**

Append to `loginlogbook-api/.env.example`:

```
# ── Grafana ───────────────────────────────────────────────────────────────────
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=replace-with-strong-password
```

- [ ] **Step 5: Verify the Compose config is valid**

```bash
cd loginlogbook-api
docker compose config --quiet
```

Expected: no output (exit code 0). If there are YAML errors, fix them before continuing.

- [ ] **Step 6: Start Grafana and verify it boots**

```bash
docker compose up grafana -d
docker compose logs grafana --tail=20
```

Expected: logs contain `HTTP Server Listen` and no `FATAL` lines. Grafana is reachable from inside the stack at `http://grafana:3000`.

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-api/grafana/provisioning/ \
        loginlogbook-api/docker-compose.yml \
        loginlogbook-api/.env.example
git commit -m "feat(grafana): add Grafana service with InfluxDB datasource provisioning"
```

---

## Task 2: nginx proxy for /grafana

**Files:**
- Modify: `loginlogbook-api/nginx/nginx.conf`

**Interfaces:**
- Consumes: `grafana` container at `http://grafana:3000` (from Task 1)
- Produces: `https://<host>/grafana/` proxies to Grafana login page

- [ ] **Step 1: Add the /grafana location block to nginx.conf**

Modify `loginlogbook-api/nginx/nginx.conf`. Add the `/grafana/` block **before** the `location /` block so nginx matches it first:

```nginx
events {}

http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;

    server {
        listen 80;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;

        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options SAMEORIGIN always;
        add_header X-Content-Type-Options nosniff always;

        location /grafana/ {
            proxy_pass http://grafana:3000/grafana/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            limit_req zone=api burst=10 nodelay;
            proxy_pass http://api:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

Note: `X-Frame-Options` changed from `DENY` to `SAMEORIGIN` — Grafana embeds iframes for panels and needs same-origin framing.

- [ ] **Step 2: Reload nginx and verify**

```bash
docker compose up nginx -d
```

Then open `https://<your-host>/grafana/` in a browser.
Expected: Grafana login page loads (302 redirect to `/grafana/login`).

- [ ] **Step 3: Log in and verify datasource**

1. Log in with `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`
2. Go to **Connections → Data sources**
3. Click **InfluxDB** → **Save & test**

Expected: green banner "datasource is working. 1 buckets found".

- [ ] **Step 4: Commit**

```bash
git add loginlogbook-api/nginx/nginx.conf
git commit -m "feat(grafana): proxy /grafana/ through nginx"
```

---

## Task 3: Dashboard JSON

**Files:**
- Create: `loginlogbook-api/grafana/dashboards/loginlogbook.json`

**Interfaces:**
- Consumes: datasource named `InfluxDB` with uid `${DS_INFLUXDB}` (from Task 1)
- Produces: dashboard `loginlogbook-main` with 10 panels in 2 rows, variables `host` and `os_user`

**Panel layout (24-column grid):**

```
y=0  [Row: Betriebsübersicht ──────────────────────── w=24]
y=1  [Logins gesamt w=8][Aktive Clients w=8][Benutzer w=8]
y=5  [Anmeldungen über Zeit ─────────────────────────w=24, h=8]
y=13 [Top-Clients ──────── w=12, h=8][Gründe w=12, h=8]
y=21 [Row: Sicherheit ──────────────────────────────── w=24]
y=22 [Tageszeit w=14,h=8][Außerh. w=5,h=4][Ohne Grund w=5,h=4]
y=30 [Login vs. Logout ──────────────────────────────w=24,h=8]
```

- [ ] **Step 1: Create the dashboard JSON file**

Create `loginlogbook-api/grafana/dashboards/loginlogbook.json` with the content below. This is the complete file — do not omit any section:

```json
{
  "__inputs": [
    {
      "name": "DS_INFLUXDB",
      "label": "InfluxDB",
      "description": "",
      "type": "datasource",
      "pluginId": "influxdb",
      "pluginName": "InfluxDB"
    }
  ],
  "__requires": [
    {"type": "datasource", "id": "influxdb", "name": "InfluxDB", "version": "1.0.0"},
    {"type": "grafana", "id": "grafana", "name": "Grafana", "version": "11.0.0"}
  ],
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": {"type": "grafana", "uid": "-- Grafana --"},
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "refresh": "30s",
  "schemaVersion": 39,
  "tags": ["loginlogbook"],
  "time": {"from": "now-24h", "to": "now"},
  "timepicker": {},
  "timezone": "browser",
  "title": "LoginLogBook",
  "uid": "loginlogbook-main",
  "version": 1,
  "templating": {
    "list": [
      {
        "name": "host",
        "label": "Client",
        "type": "query",
        "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
        "definition": "import \"influxdata/influxdb/schema\"\nschema.tagValues(bucket: \"logins\", tag: \"host\")",
        "query": {
          "query": "import \"influxdata/influxdb/schema\"\nschema.tagValues(bucket: \"logins\", tag: \"host\")",
          "refId": "StandardVariableQuery"
        },
        "multi": true,
        "includeAll": true,
        "allValue": ".*",
        "sort": 1,
        "refresh": 2,
        "hide": 0,
        "current": {}
      },
      {
        "name": "os_user",
        "label": "Benutzer",
        "type": "query",
        "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
        "definition": "import \"influxdata/influxdb/schema\"\nschema.tagValues(bucket: \"logins\", tag: \"os_user\")",
        "query": {
          "query": "import \"influxdata/influxdb/schema\"\nschema.tagValues(bucket: \"logins\", tag: \"os_user\")",
          "refId": "StandardVariableQuery"
        },
        "multi": true,
        "includeAll": true,
        "allValue": ".*",
        "sort": 1,
        "refresh": 2,
        "hide": 0,
        "current": {}
      }
    ]
  },
  "panels": [
    {
      "id": 1,
      "title": "Betriebsübersicht",
      "type": "row",
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
      "panels": []
    },
    {
      "id": 2,
      "title": "Logins gesamt",
      "type": "stat",
      "gridPos": {"h": 4, "w": 8, "x": 0, "y": 1},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["sum"], "fields": "", "values": false},
        "textMode": "auto"
      },
      "fieldConfig": {
        "defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "blue", "value": null}]}}
      },
      "targets": [
        {
          "refId": "A",
          "query": "from(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\" and r.event_type == \"login\")\n  |> filter(fn: (r) => r.host =~ /^${host:regex}$/)\n  |> filter(fn: (r) => r.os_user =~ /^${os_user:regex}$/)\n  |> count()"
        }
      ]
    },
    {
      "id": 3,
      "title": "Aktive Clients",
      "type": "stat",
      "gridPos": {"h": 4, "w": 8, "x": 8, "y": 1},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": false},
        "textMode": "auto"
      },
      "fieldConfig": {
        "defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}]}}
      },
      "targets": [
        {
          "refId": "A",
          "query": "from(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\")\n  |> keep(columns: [\"host\"])\n  |> distinct(column: \"host\")\n  |> count()"
        }
      ]
    },
    {
      "id": 4,
      "title": "Aktive Benutzer",
      "type": "stat",
      "gridPos": {"h": 4, "w": 8, "x": 16, "y": 1},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": false},
        "textMode": "auto"
      },
      "fieldConfig": {
        "defaults": {"color": {"mode": "thresholds"}, "thresholds": {"mode": "absolute", "steps": [{"color": "purple", "value": null}]}}
      },
      "targets": [
        {
          "refId": "A",
          "query": "from(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\")\n  |> keep(columns: [\"os_user\"])\n  |> distinct(column: \"os_user\")\n  |> count()"
        }
      ]
    },
    {
      "id": 5,
      "title": "Anmeldungen über Zeit",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 24, "x": 0, "y": 5},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "options": {
        "legend": {"calcs": ["sum"], "displayMode": "list", "placement": "bottom"},
        "tooltip": {"mode": "single", "sort": "none"}
      },
      "fieldConfig": {
        "defaults": {
          "custom": {"drawStyle": "bars", "fillOpacity": 60, "lineWidth": 1, "spanNulls": false},
          "color": {"mode": "palette-classic"}
        }
      },
      "targets": [
        {
          "refId": "A",
          "query": "from(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\" and r.event_type == \"login\")\n  |> filter(fn: (r) => r.host =~ /^${host:regex}$/)\n  |> filter(fn: (r) => r.os_user =~ /^${os_user:regex}$/)\n  |> aggregateWindow(every: v.windowPeriod, fn: count, createEmpty: false)"
        }
      ]
    },
    {
      "id": 6,
      "title": "Top-Clients",
      "type": "barchart",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 13},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "options": {
        "barWidth": 0.7,
        "fillOpacity": 80,
        "gradientMode": "none",
        "legend": {"displayMode": "list", "placement": "bottom"},
        "orientation": "horizontal",
        "tooltip": {"mode": "single", "sort": "none"},
        "xTickLabelRotation": 0
      },
      "fieldConfig": {
        "defaults": {"color": {"mode": "palette-classic"}}
      },
      "targets": [
        {
          "refId": "A",
          "query": "from(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\" and r.event_type == \"login\")\n  |> filter(fn: (r) => r.os_user =~ /^${os_user:regex}$/)\n  |> group(columns: [\"host\"])\n  |> count()\n  |> group()\n  |> sort(columns: [\"_value\"], desc: true)\n  |> limit(n: 10)\n  |> rename(columns: {\"host\": \"_field\"})"
        }
      ]
    },
    {
      "id": 7,
      "title": "Anmeldegründe",
      "type": "piechart",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 13},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "options": {
        "displayLabels": ["percent"],
        "legend": {"displayMode": "table", "placement": "right", "values": ["value", "percent"]},
        "pieType": "pie",
        "tooltip": {"mode": "single", "sort": "none"}
      },
      "targets": [
        {
          "refId": "A",
          "query": "from(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\" and r.event_type == \"login\")\n  |> filter(fn: (r) => exists r.reason)\n  |> filter(fn: (r) => r.host =~ /^${host:regex}$/)\n  |> filter(fn: (r) => r.os_user =~ /^${os_user:regex}$/)\n  |> group(columns: [\"reason\"])\n  |> count()\n  |> group()\n  |> rename(columns: {\"reason\": \"_field\"})"
        }
      ]
    },
    {
      "id": 8,
      "title": "Sicherheit",
      "type": "row",
      "collapsed": false,
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 21},
      "panels": []
    },
    {
      "id": 9,
      "title": "Anmeldungen nach Tageszeit (Stunde)",
      "type": "barchart",
      "gridPos": {"h": 8, "w": 14, "x": 0, "y": 22},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "description": "Anzahl Logins pro Stunde des Tages (0–23). Zeigt Aktivitätsmuster und Ausreißer.",
      "options": {
        "barWidth": 0.9,
        "fillOpacity": 70,
        "gradientMode": "none",
        "legend": {"displayMode": "hidden", "placement": "bottom"},
        "orientation": "vertical",
        "tooltip": {"mode": "single", "sort": "none"},
        "xTickLabelRotation": 0
      },
      "fieldConfig": {
        "defaults": {"color": {"fixedColor": "blue", "mode": "fixed"}}
      },
      "targets": [
        {
          "refId": "A",
          "query": "import \"date\"\nfrom(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\" and r.event_type == \"login\")\n  |> filter(fn: (r) => r.host =~ /^${host:regex}$/)\n  |> filter(fn: (r) => r.os_user =~ /^${os_user:regex}$/)\n  |> map(fn: (r) => ({_time: r._time, _value: 1, _field: string(v: date.hour(t: r._time))}))\n  |> group(columns: [\"_field\"])\n  |> sum()\n  |> group()\n  |> sort(columns: [\"_field\"])"
        }
      ]
    },
    {
      "id": 10,
      "title": "Außerhalb Geschäftszeiten",
      "type": "stat",
      "gridPos": {"h": 4, "w": 5, "x": 14, "y": 22},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "description": "Logins vor 07:00 oder nach 19:00 Uhr.",
      "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["sum"], "fields": "", "values": false},
        "textMode": "auto"
      },
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "yellow", "value": 1},
              {"color": "red", "value": 10}
            ]
          }
        }
      },
      "targets": [
        {
          "refId": "A",
          "query": "import \"date\"\nfrom(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\" and r.event_type == \"login\")\n  |> filter(fn: (r) => r.host =~ /^${host:regex}$/)\n  |> filter(fn: (r) => r.os_user =~ /^${os_user:regex}$/)\n  |> map(fn: (r) => ({r with hour: date.hour(t: r._time)}))\n  |> filter(fn: (r) => r.hour < 7 or r.hour > 19)\n  |> count()"
        }
      ]
    },
    {
      "id": 11,
      "title": "Logins ohne Grund",
      "type": "stat",
      "gridPos": {"h": 4, "w": 5, "x": 19, "y": 22},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "description": "Login-Events ohne gesetzten Auswahlgrund.",
      "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["sum"], "fields": "", "values": false},
        "textMode": "auto"
      },
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "yellow", "value": 1},
              {"color": "red", "value": 5}
            ]
          }
        }
      },
      "targets": [
        {
          "refId": "A",
          "query": "from(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\" and r.event_type == \"login\")\n  |> filter(fn: (r) => not exists r.reason)\n  |> filter(fn: (r) => r.host =~ /^${host:regex}$/)\n  |> filter(fn: (r) => r.os_user =~ /^${os_user:regex}$/)\n  |> count()"
        }
      ]
    },
    {
      "id": 12,
      "title": "Login vs. Logout",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 24, "x": 0, "y": 30},
      "datasource": {"type": "influxdb", "uid": "${DS_INFLUXDB}"},
      "description": "Logins und Logouts überlagert im Zeitverlauf.",
      "options": {
        "legend": {"calcs": ["sum"], "displayMode": "list", "placement": "bottom"},
        "tooltip": {"mode": "multi", "sort": "none"}
      },
      "fieldConfig": {
        "defaults": {
          "custom": {"drawStyle": "bars", "fillOpacity": 50, "lineWidth": 1, "spanNulls": false},
          "color": {"mode": "palette-classic"}
        }
      },
      "targets": [
        {
          "refId": "A",
          "query": "from(bucket: \"logins\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"login_events\")\n  |> filter(fn: (r) => r.host =~ /^${host:regex}$/)\n  |> filter(fn: (r) => r.os_user =~ /^${os_user:regex}$/)\n  |> group(columns: [\"event_type\"])\n  |> aggregateWindow(every: v.windowPeriod, fn: count, createEmpty: false)\n  |> group()"
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Reload the dashboard provider**

Grafana polls `updateIntervalSeconds: 60` automatically. To force an immediate reload:

```bash
docker compose restart grafana
docker compose logs grafana --tail=10
```

Expected: log line `Provisioning of dashboards started` followed by `Provisioning file ... done`.

- [ ] **Step 3: Verify the dashboard in the browser**

1. Open `https://<your-host>/grafana/`
2. Navigate to **Dashboards → LoginLogBook → LoginLogBook**
3. Set time range to **Last 7 days** to ensure data is visible
4. Verify all 10 panels render without "No data" errors
5. Test the `Client` and `Benutzer` variable dropdowns — selecting a value should filter all panels

- [ ] **Step 4: Commit**

```bash
git add loginlogbook-api/grafana/dashboards/loginlogbook.json
git commit -m "feat(grafana): add LoginLogBook dashboard with 10 panels"
```

---

## Self-Review

**Spec coverage:**
- ✅ Grafana 11 container in Compose
- ✅ InfluxDB Flux datasource provisioned
- ✅ Dashboard provisioned from file
- ✅ Variables: `host` (multi, All), `os_user` (multi, All)
- ✅ Row 1: Logins gesamt, Aktive Clients, Aktive Benutzer, Über Zeit, Top-Clients, Gründe
- ✅ Row 2: Tageszeit, Logins ohne Grund, Login vs. Logout, Außerhalb Geschäftszeiten
- ✅ nginx `/grafana/` proxy
- ✅ `.env.example` additions
- ✅ Default time range: now-24h
- ✅ No API/client code changes

**Notes for implementer:**
- If panels show "No data", verify the datasource test passes first (Task 2, Step 3)
- The `${host:regex}` / `${os_user:regex}` variable syntax requires the InfluxDB datasource Flux mode — it substitutes selected values as a pipe-separated regex (e.g., `host1|host2`) or `.*` for "All"
- `X-Frame-Options` in nginx changed from `DENY` to `SAMEORIGIN` to allow Grafana panel iframes
