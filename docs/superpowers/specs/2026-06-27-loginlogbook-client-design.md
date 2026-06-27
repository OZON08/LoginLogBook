# LoginLogBook Client — Design Specification

**Date:** 2026-06-27
**Status:** Draft for review
**Component:** `loginlogbook-client` (PyQt6 fullscreen overlay)

---

## 1. Purpose

The LoginLogBook client is a fullscreen overlay that launches automatically at OS login on Windows and Linux. It blocks desktop access until the user selects a reason for logging in and clicks "Anmelden". Login and logout events are reported to the central API. The overlay displays a list of recent logins from the same host for situational awareness.

---

## 2. Layout

The screen is fully covered by a dark semi-transparent overlay (no desktop access, no taskbar). Centered on the overlay sits a single **Card** containing all interactive elements.

```
┌──────────────────────────────────────────────────────────────────────┐  FULLSCREEN
│                                                                      │  rgba(15,23,42,0.88)
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │                      [LOGO vom API]                          │   │
│   ├───────────────────────────┬──────────────────────────────────┤   │
│   │  ┌─────────────────────┐  │  Letzte Anmeldungen              │   │
│   │  │ 🔍 Grund suchen...  │  │  Letzte 7 Tage                   │   │
│   │  └─────────────────────┘  │  ────────────────────────────    │   │
│   │                           │  26.06. 08:14  karsten  Wartung  │   │
│   │  Wartung                  │  26.06. 07:55  mueller  Deploy.  │   │
│   │  Deployment               │  25.06. 17:30  karsten  Monitor. │   │
│   │ ▶ Incident    ← gewählt   │  25.06. 09:11  schmidt  Incident │   │
│   │  Monitoring               │  ...                             │   │
│   │  ...          (scrollbar) │                    (scrollbar)   │   │
│   │                           │                                  │   │
│   │  [ Abmelden ]  [ Anmelden]│                                  │   │
│   ├───────────────────────────┴──────────────────────────────────┤   │
│   │  karsten · SRV01                                    ● Online  │   │
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Card dimensions:** 920 px wide, height auto (max 85 vh), zentriert.
**Columns:** Left ~52 % (reason selection), Right ~48 % (recent logins), separated by a 1 px vertical border.

---

## 3. Visual Design System

### 3.1 Color Tokens

| Token | Hex / Value | Usage |
|---|---|---|
| `--color-overlay-bg` | `rgba(15, 23, 42, 0.88)` | Fullscreen background over desktop |
| `--color-card-bg` | `#FFFFFF` | Card background |
| `--color-primary` | `#2563EB` | Anmelden button, selection highlight, focus ring |
| `--color-primary-hover` | `#1D4ED8` | Hover state on primary button |
| `--color-primary-disabled` | `#2563EB` at 38 % opacity | Anmelden button before reason selected |
| `--color-foreground` | `#0F172A` | Primary text |
| `--color-muted` | `#64748B` | Footer text, timestamps, secondary labels |
| `--color-border` | `#E2E8F0` | Card divider, list item separator |
| `--color-selection-bg` | `#EFF6FF` | Selected list item background |
| `--color-selection-border` | `#2563EB` | 3 px left border on selected item |
| `--color-destructive` | `#DC2626` | Abmelden button border/text |
| `--color-status-online` | `#16A34A` | Status dot — API reachable |
| `--color-status-offline` | `#CA8A04` | Status dot — offline/cache mode |
| `--color-brand-accent` | injected from API | Overrides `--color-primary` when provided |

> **Branding:** The accent color is a planned future API field (`brand_color`). When provided by `GET /branding/config`, it overrides `--color-primary` across the entire card.

### 3.2 Typography

- **Font family:** `"Segoe UI", system-ui, sans-serif` — system font, no download required, immediately available on both Windows and Linux (falls back to DE system font)
- **Font scale:**

| Usage | Size | Weight |
|---|---|---|
| Footer, timestamps | 11 px | 400 |
| List items, table content | 13 px | 400 (normal) / 500 (selected) |
| Column headers | 13 px | 600 |
| Search field, table body | 15 px | 400 |
| Button labels | 15 px | 600 |
| Section header ("Letzte Anmeldungen") | 16 px | 600 |
| Logo fallback text | 22 px | 600 |

- **Line height:** 1.5 body, 1.2 buttons
- **Timestamps:** tabular figures (monospaced numbers) to prevent column shift

### 3.3 Card Shape & Elevation

- `border-radius: 12px`
- `box-shadow: 0 24px 64px rgba(0, 0, 0, 0.35)`
- `padding: 32px`
- Column gap: 24 px, with 1 px `--color-border` vertical divider

---

## 4. Components

### 4.1 Logo Area (top of card, full width)

- Centered, max `160 × 72 px`, loaded from API (`GET /branding/logo`) with local cache
- Skeleton placeholder (gray shimmer, 120 × 56 px) while loading
- Fallback: app name "LoginLogBook" in 22 px semibold when no logo is cached and API unreachable

### 4.2 Search Field (left column)

- Magnifier icon (SVG, 16 px) on the left inside the field
- Placeholder: `Grund suchen…`
- Live filter: 150 ms debounce, filters reason list as user types
- `Escape` key clears the field and restores full list
- Focus is set to the search field automatically on app start

### 4.3 Reason List (left column)

- Scrollable list; scrollbar visible when content exceeds ~6 items
- Each item: full-width clickable row, 44 px min height (touch/click target)
- **Selected state:** `--color-selection-bg` background + 3 px left border in `--color-selection-border` + font-weight 500
- **Hover state:** subtle background tint `#F8FAFC`, 150 ms transition
- **Keyboard navigation:** `↑`/`↓` arrow keys move selection; `Enter` confirms selection
- **No results state:** centered muted text — `Kein Grund gefunden für „[query]"`

### 4.4 Button Row (left column, bottom)

Two equally-sized buttons, full width of left column split 50/50:

| Button | Style | Behavior |
|---|---|---|
| **Abmelden** | Outline, border + text `--color-destructive` | Triggers OS logoff immediately; no event recorded; shows confirmation dialog first |
| **Anmelden** | Filled `--color-primary`, white text | Disabled (38 % opacity, not clickable) until a reason is selected; on click → spinner + disabled state → POST event → overlay closes |

- Button height: 44 px, `border-radius: 8px`
- Anmelden loading state: spinner replaces label text, button stays disabled
- Error state: brief red message below buttons — `Anmeldung konnte nicht übermittelt werden – wird wiederholt`; overlay still closes and desktop is released

### 4.5 Abmelden Confirmation Dialog

A modal dialog (smaller card on top of the overlay) before OS logoff:

- Title: `Wirklich abmelden?`
- Body: `Es wird kein Anmeldungsgrund erfasst.`
- Buttons: `Abbrechen` (secondary) | `Abmelden` (destructive/red, filled)

### 4.6 Recent Logins Table (right column)

- Header: `Letzte Anmeldungen` (16 px semibold) + `Letzte X Tage` (13 px muted) — X from `GET /config`
- Column headers: `Datum / Uhrzeit` · `Benutzer` · `Grund`
- Rows: newest first, scrollable
- Timestamp format: `DD.MM. HH:MM` (tabular figures)
- Skeleton: 4–5 shimmer rows while loading
- **Empty state:** `Keine Anmeldungen in diesem Zeitraum` — centered, muted

### 4.7 Footer (full width, below both columns)

- Left: `[os_user] · [hostname]` — 11 px, `--color-muted`
- Right: status dot + label
  - `● Online` — `--color-status-online`
  - `● Offline – Cache` — `--color-status-offline`; tooltip shows timestamp of last successful API contact

---

## 5. States

### 5.1 Startup / Loading

1. App opens fullscreen immediately (overlay blocks desktop)
2. Skeleton placeholders shown for logo, reason list, and recent logins table
3. API requests fire in parallel: logo, reasons, recent logins, config (for X days)
4. Components populate as responses arrive; skeletons fade out

### 5.2 Online (normal)

- All data from API, cached locally after each successful fetch
- Status dot: green

### 5.3 Offline / API unreachable

- Reasons: served from local cache; status dot yellow; tooltip shows cache age
- Logo: served from cache or bundled fallback
- Recent logins: served from cache with timestamp note
- Event POST after login: written to local file-backed queue; retried on reconnect
- **The login flow is never blocked** — desktop is always released after Anmelden

### 5.4 Anmelden Flow

1. User selects reason (click or keyboard) → button activates
2. User clicks Anmelden (or presses Enter) → spinner, button disabled
3. `POST /events` fires with `event_type=login`, `host`, `os_user`, `reason`, `timestamp`
4. On success OR failure (503): overlay closes, desktop released, Task Manager lock lifted
5. On failure: event queued locally for retry

### 5.5 Abmelden Flow

1. User clicks Abmelden → confirmation dialog appears
2. User confirms → OS logoff triggered; no event recorded; overlay closes

---

## 6. Keyboard & Accessibility

| Key | Action |
|---|---|
| (App start) | Focus on search field |
| `↑` / `↓` | Navigate reason list |
| `Enter` | Select focused reason (or confirm Anmelden if reason already selected) |
| `Escape` | Clear search field |
| `Tab` | Search → List → Abmelden → Anmelden |
| `Space` | Activate focused button |

- All interactive elements have visible focus rings (2 px `--color-primary` outline, 2 px offset)
- Selection state conveyed by both color and left border (not color alone)
- Status dot state conveyed by label text as well as color
- Disabled Anmelden button has `aria-disabled` + `cursor: not-allowed`

---

## 7. Platform Behavior

### 7.1 Windows

| Concern | Solution |
|---|---|
| Fullscreen over taskbar | `Qt.WindowType.WindowStaysOnTopHint` + WinAPI `SetWindowPos(HWND_TOPMOST)` |
| No window frame | `Qt.WindowType.FramelessWindowHint` |
| Task Manager block | Set `HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System\DisableTaskMgr = 1` on open; reset on close |
| Autostart | Group Policy (GPO) logon script or Scheduled Task at user logon |

### 7.2 Linux

**Display server detection:** At startup, check `WAYLAND_DISPLAY`. If set, force XWayland mode: `QT_QPA_PLATFORM=xcb`. Log a warning to the event log.

| Concern | X11 | Wayland |
|---|---|---|
| Fullscreen over everything | `Qt.WindowType.BypassWindowManagerHint` | XWayland fallback |
| Keyboard grab | `XGrabKeyboard` + `XGrabPointer` at X server level | Not possible natively |
| Intercepted key combos | Alt+F4, Alt+Tab, Super, Ctrl+Esc, Ctrl+Alt+T, Ctrl+C, Ctrl+Z | Not interceptable without XWayland |
| TTY switching (Ctrl+Alt+F1–F6) | **Not interceptable** (kernel level) | **Not interceptable** |
| Autostart | `/etc/xdg/autostart/loginlogbook-client.desktop` (system-wide) | Same |
| Focus restore on close | `XUngrabKeyboard` + `XUngrabPointer` | N/A |

**Accepted Linux limitations (documented, not defects):**
- TTY switching bypasses the overlay
- `kill -9` as root bypasses the overlay
- Wayland-native mode without XWayland is a future feature, not in this version
- Physical access is out of scope (same as Windows, per design spec §6)

---

## 8. API Dependencies

| Endpoint | Used for | Fallback |
|---|---|---|
| `GET /branding/logo` | Logo image | Local cache → bundled default |
| `GET /reasons` | Reason list | Local cache |
| `GET /events/recent?host=&days=` | Recent logins table | Local cache |
| `GET /config` | `recent_days` value for table header | Default: 7 days |
| `POST /events` | Login / logout event | Local file queue + retry |

> **Note:** `GET /config` and the `days` parameter on `GET /events/recent` are new endpoints not yet in the API plan. They must be added in the API implementation as a prerequisite for the client.

---

## 9. New API Requirements (Client-Driven)

The following additions to `loginlogbook-api` are required before the client can be fully implemented:

1. **`GET /config`** — returns `{"recent_days": 7}` (admin-configurable). Allows central control of the recent-logins window shown in all overlays.
2. **`GET /events/recent` — add `days` query parameter** — filters events to the last N days instead of a fixed count. The current `limit` (count cap) is kept as an additional guard.
3. **`GET /branding/config` (future)** — optional endpoint returning `{"brand_color": "#005BAC"}` to inject an accent color override. Not required for v1.

---

## 10. Testing Strategy

- **Unit tests:** Reason filter logic, cache read/write, event queue serialization — all independent of GUI
- **API client tests:** Each API call mocked; test online, offline, and 503 responses
- **GUI smoke test:** Overlay opens fullscreen, reason list populates, Anmelden activates after selection, overlay closes
- **Platform test (Windows):** Task Manager blocked while open; released on close; registry value reset on crash/force-quit via cleanup hook
- **Platform test (Linux/X11):** Keyboard grab active; Alt+Tab intercepted; released on close
