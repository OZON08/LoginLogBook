# LoginLogBook — Design Specification

**Date:** 2026-06-26
**Status:** Draft for review

## 1. Purpose

LoginLogBook records *why* people log into servers. On Windows and Linux
machines, an application launches automatically after the OS login and
presents a fullscreen overlay. The user must select a reason before gaining
access to the desktop. Login and logout events are stored centrally in
InfluxDB. Each server can display its own recent logins, and a CLI tool
allows detailed queries.

## 2. Scope & Non-Goals

**In scope:**
- Fullscreen login overlay launched at OS login (autostart).
- Reason selection (mandatory) before desktop access.
- "Abmelden" (sign-off) button that triggers an OS logoff without recording a login.
- Automatic logout event on OS shutdown/logoff.
- Central FastAPI backend managing reasons and events.
- InfluxDB for event storage.
- Recent-logins display in the overlay and via a CLI tool.
- Task Manager lock-down while the overlay is open.

**Non-goals:**
- Guaranteed protection against a local administrator/root user with physical
  access. The lock-down raises the bar but is explicitly **not** a hard
  security boundary (see §6).
- User authentication/identity management — the OS user is taken as-is.
- Reporting dashboards or analytics UI beyond "recent logins".

## 3. Architecture

**Thin client + central API.** Clients talk only to the FastAPI backend.
InfluxDB is reachable only from the backend, so no database credentials live
on client machines.

```
[Client: PyQt6 overlay]            [CLI: loginlog]
        │                                  │
        ▼ HTTP                             ▼ HTTP
              [FastAPI backend] ──────► [InfluxDB]
                    │
                    ├── Reasons (CRUD)
                    ├── Login / Logout events (write)
                    └── Recent logins (query)
```

### Components

| Component | Purpose | Stack |
|---|---|---|
| `loginlogbook-client` | PyQt6 fullscreen overlay on each server. Shows login form, reasons, recent logins. Locks Task Manager. | Python + PyQt6 |
| `loginlogbook-api` | Central backend. Manages reasons (CRUD), ingests login/logout events, serves recent logins. Only component with InfluxDB access. | Python + FastAPI, Docker |
| `loginlogbook-cli` | Terminal tool (`loginlog show`) for detailed recent-login queries per host. | Python (Typer) |
| InfluxDB | Time-series store for events. Set up via docker-compose alongside the API. | InfluxDB 2.x, Docker |

Each component is independently testable through well-defined HTTP interfaces.

## 4. Data Model (InfluxDB)

**Measurement: `login_events`**
- Tags: `host`, `os_user`, `event_type` (`login` | `logout`), `reason` (login only)
- Fields: `count` (1) — events are points in time
- Timestamp: event time (UTC)

Reasons are managed by the API. Storage of the reasons list itself: a simple
persisted store on the API side (JSON file or InfluxDB measurement
`reasons`) — final choice deferred to the implementation plan; the API
contract below is what clients depend on.

## 5. API Contract

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/reasons` | List active login reasons. |
| `POST` | `/reasons` | Create a reason (admin). |
| `DELETE` | `/reasons/{id}` | Deactivate/remove a reason (admin). |
| `POST` | `/events` | Record a login or logout event. Body: `{event_type, host, os_user, reason?, timestamp}`. |
| `GET` | `/events/recent` | Recent events. Query: `host`, `limit`, optional `event_type`. |
| `GET` | `/health` | Liveness/readiness, including InfluxDB reachability. |

Admin endpoints are protected by a shared admin token; clients use a separate
read/write client token. Tokens are configured via environment variables.

## 6. Task Manager Lock-Down

**Windows:**
- Set registry value `DisableTaskMgr` (HKCU policy) while the overlay is open;
  reset on close.
- Overlay window is fullscreen, topmost, always-on-top, with no close affordance.
- Rolled out via Group Policy.

**Linux:**
- Fullscreen kiosk window (override-redirect) that grabs focus and intercepts
  key combinations.
- Autostart and enforcement via systemd / desktop-autostart entries.

**Explicit limitation:** A user with full administrator/root rights and
physical access can ultimately bypass these measures. The design deliberately
raises the effort required but is **not** a guarantee against a privileged
local user. This is an accepted boundary, not a defect.

## 7. Data Flow

**Login (sign-in):**
1. App autostarts → fullscreen overlay, Task Manager locked.
2. App fetches reasons (`GET /reasons`); falls back to local cache if offline.
3. User selects a reason and clicks "Anmelden".
4. `POST /events` with `event_type=login`, host, os_user, reason, timestamp.
5. Overlay closes, desktop is released, Task Manager lock is lifted.

**Sign-off (does not want to log in):**
- User clicks "Abmelden" → OS logoff is triggered → no event recorded.

**Logout (automatic):**
- OS shutdown/logoff hook → `POST /events` with `event_type=logout`.

**Recent logins:**
- Overlay: `GET /events/recent?host=<host>&limit=5` → short summary on screen.
- CLI: `loginlog show --host <host> --limit 20` → table in terminal.

## 8. Offline Behaviour & Error Handling

- **Reasons unreachable:** use the last successfully fetched list from local cache.
- **Event POST fails:** event is written to a local file-backed queue and
  retried on next successful contact. **The login flow is never blocked** —
  the desktop is released regardless.
- **API ↔ InfluxDB error:** API returns 503; client treats it like an offline
  event POST (queue + retry).

Accepted decision: availability is prioritised over strict enforcement —
inability to reach the server must not prevent a user from working.

## 9. Deployment

- **Server side:** docker-compose with two services — `loginlogbook-api` and
  `influxdb`. Configuration (tokens, org, bucket, URLs) via environment / `.env`.
- **Client side:** packaged Python app with autostart configuration. Windows
  rollout via Group Policy; Linux via systemd / autostart entries managed by
  the central configuration management.

## 10. Testing Strategy

- **API:** unit tests for endpoints with InfluxDB mocked; one integration test
  against a real InfluxDB container.
- **Client:** core logic (event queue, reasons cache, API client) tested
  independently of the GUI; a GUI smoke test for the overlay.
- **CLI:** output formatting tested against a mocked API.

## 11. Open Questions / Deferred Decisions

- Reasons persistence: JSON file vs. InfluxDB measurement (decide in plan).
- Exact OS-logoff hook mechanism per platform (decide in plan).
- Packaging tool for the client (PyInstaller vs. alternatives) — decide in plan.
