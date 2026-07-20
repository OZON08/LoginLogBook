# GNOME-konformer Wayland-Desktop-Lock — Design

**Datum:** 2026-07-20
**Status:** Genehmigt (Design), bereit für Implementierungsplan
**Komponente:** `loginlogbook-gnome-extension/` (neu)

## Ziel

Der LoginLogBook-Login-Grund soll unter **GNOME/Wayland** echt erzwungen werden:
Der Nutzer muss beim Session-Start einen Login-Grund bestätigen (oder sich
abmelden), bevor der Desktop freigegeben wird. Der bisherige X11-`grab_keyboard()`
in `loginlogbook-client/app/platform_linux.py` ist unter Wayland wirkungslos —
und wird zudem nirgends im Client aufgerufen (toter Code).

## Ausgangslage / Befund

- Der PyQt-Client ist ein **xdg-Autostart-Programm** (`/etc/xdg/autostart/`) und
  startet **innerhalb** der bereits laufenden GNOME-Session.
- `lock()` / `unlock()` / `setup_fullscreen()` werden im Client **nie aufgerufen**;
  das Overlay „blockiert" nur per `showFullScreen()` — unter Wayland kein Zwang.
- Ein Wayland-Client kann den Compositor per Design **nicht** global grabben.
  Einzig eine **GNOME-Shell-Extension** kann in-session einen echten Input-Grab
  setzen (`Main.pushModal`, wie der Sperrbildschirm).

## Zielumgebung

- GNOME Shell **50.1**, gjs **1.88**, **Soup-3.0**-Typelib vorhanden, Ubuntu 26.04 LTS.
- ESM-Extension (`import … from 'gi://…'`, `export default class extends Extension`).
- `metadata.json` mit `shell-version: ["50"]`.

## Entscheidungen (aus dem Brainstorming)

1. **Erzwingungs-Ebene:** In-Session via GNOME-Shell-Extension (nicht Greeter/PAM).
2. **UI-Umfang:** **Voll-Parität** zum PyQt-Overlay.
3. **Config-Quelle:** bestehende **`/etc/loginlogbook.env`** wiederverwenden.
4. **Architektur:** Ansatz A — eigenständige GJS-Extension mit sauberem Modul-Split;
   spricht direkt die `loginlogbook-api`. Der PyQt-Client bleibt für X11/Windows
   unverändert. Kein Laufzeit-Prozesswechsel.

## Nicht-Ziele

- Kein Umbau des PyQt-Clients (bleibt für X11 #18 und Windows #17 zuständig).
- Kein Greeter-/PAM-/GDM-Eingriff (bewusst außerhalb des Scopes).
- Kein Blocken von VT-Wechsel (Ctrl+Alt+Fn) oder Power-Taste — liegt bei
  Kernel/logind und ist aus einer Extension nicht abfangbar (siehe Restlücken).

## Architektur & Modul-Layout

Neue Geschwister-Komponente `loginlogbook-gnome-extension/`, UUID
`loginlogbook@willeke.tv`.

```
loginlogbook-gnome-extension/
  metadata.json            # uuid, name, description, shell-version ["50"], url
  extension.js             # default class extends Extension; enable()/disable()
  src/
    enforcement.js         # ModalGuard: pushModal-Grab, Vollbild-Cover, Re-Assert
    config.js              # parseEnvFile('/etc/loginlogbook.env')
    net.js                 # ApiClient (Soup 3)
    models.js              # Reason/EventIn/EventOut/AppConfig/BrandingConfig/LanguageSetting
    store.js               # Cache + Queue
    i18n.js                # Translator (aktiv -> de -> key)
    ui/
      overlay.js           # Vollbild-Overlay + zentrierte Karte, Skeleton/Loading
      reasonList.js        # durchsuchbare Grundliste
      recentTable.js       # Recent-Events-Tabelle
      footer.js            # user@host, Online/Offline, Version
      logo.js              # Branding-Logo
      confirmDialog.js     # Abmelden-Bestätigung
  locales/ de.json en.json # Kopien der Client-Locales + Paritäts-Test
  tests/                   # headless gjs-Unit-Tests
  packaging/
    install.sh uninstall.sh
  README.md
```

Jedes Modul hat eine klar umrissene Aufgabe und eine testbare Schnittstelle. Die
UI-Module hängen nur von `models.js`/`i18n.js` ab; `net.js`/`store.js`/`config.js`
sind UI-frei und headless testbar.

## Lebenszyklus

Läuft nur im `user`-Session-Mode (Standard), **nicht** auf dem Sperrbildschirm.

- **`enable()`** (Shell lädt die Extension beim Session-Start):
  1. Config aus `/etc/loginlogbook.env` laden. Bei Fehler/fehlender `API_URL`:
     **fail open** — kein Grab, Fehler ins Journal, `enable()` endet ruhig.
  2. `ApiClient`, `Store`, `Translator`, `Overlay` konstruieren.
  3. **Grab starten** (`ModalGuard.engage()`), Overlay über alle Monitore zeigen.
  4. Sofort aus Cache befüllen (Footer offline), dann async von der API nachladen.
- **Grund gewählt + Anmelden** → Event posten (offline: enqueue) → Queue flushen →
  `ModalGuard.release()` + Overlay zerstören. Die restliche Session ist frei.
- **Abmelden** → `confirmDialog` → `loginctl terminate-session $XDG_SESSION_ID`
  (Fallback `pkill -KILL -u $USER`).
- **`disable()`** (Shell-Unload) → Grab lösen + Overlay/Signale/Async sauber
  abbauen (GNOME-Pflicht: keine Ressourcen-Lecks).

Semantik ist „einmal pro Login": `enable()` läuft einmal je Session-Start; unter
Wayland gibt es keinen Live-Shell-Reload.

## Enforcement (`ModalGuard`)

- `Main.pushModal(overlayActor, { actionMode: Shell.ActionMode.SYSTEM_MODAL })` —
  greift Tastatur+Maus auf den Overlay-Aktor und blockiert dadurch
  Super/Overview/Keybindings/Alt+Tab/Workspace-Wechsel.
- Overlay-Cover für **jeden** Monitor aus `Main.layoutManager.monitors`; auf
  `monitors-changed` neu layouten; falls der Grab verloren geht, **Re-Push**.
- `release()` gibt den Modal frei (`Main.popModal`) und ist idempotent.
- **Restlücken (dokumentiert, nicht behebbar aus einer Extension):** VT-Wechsel
  (Ctrl+Alt+Fn), Power-Taste, Magic-SysRq. Eine echte Härtung dagegen wäre
  logind/PAM und ist ausdrücklich außerhalb dieses Scopes.

## Daten-Layer

### `config.js`
Parst `/etc/loginlogbook.env` (`KEY=VALUE`, `#`-Kommentare, optionale Quotes) zu
`{ apiUrl, clientToken, caBundle, cacheDir, queueFile }`. Übernimmt dieselben
Variablen wie der PyQt-Client — `API_URL`, `CLIENT_TOKEN`, `API_CA_BUNDLE`,
`CACHE_DIR`, `QUEUE_FILE` — mit **denselben Defaults**
(`~/.loginlogbook/cache`, `~/.loginlogbook/queue.json`). Dadurch teilen sich
Extension und PyQt-Client Cache und Queue.

### `net.js` — `ApiClient` (Soup 3)
`Soup.Session` mit `timeout = 5`, Header `X-Client-Token: <clientToken>`,
CA-Bundle via `Gio.TlsDatabase` aus `caBundle` (falls gesetzt). Requests async
über `send_and_read_async`. Der `Soup.Session` ist **injizierbar**, damit Tests
ihn mocken können (Analogie zum `httpx`-Transport des PyQt-Clients).

| Methode | Request | Antwort |
|---|---|---|
| `getReasons()` | GET `/reasons` | `[{id,label,active}]` |
| `getLogo()` | GET `/branding/logo` | bytes + content-type |
| `getConfig()` | GET `/config` | `{recent_days, allow_free_text}` |
| `getBrandingConfig()` | GET `/branding/config` | `{logo_height, logo_bg}` |
| `getSettings()` | GET `/settings` | `{language, available[]}` |
| `getRecentEvents(host, days)` | GET `/events/recent?host&days&limit=100` | `[EventOut]` |
| `postEvent(evt)` | POST `/events` (JSON `EventIn`) | — |

### `models.js`
Spiegelt `loginlogbook-client/app/models.py`:
- `Reason { id, label, active=true }`
- `EventIn { event_type, host, os_user, reason?, timestamp }`, `event_type ∈ {login, logout}`
- `EventOut { … dieselben Felder }`
- `AppConfig { recent_days=7, allow_free_text=true }`
- `BrandingConfig { logo_height=120, logo_bg="#1E293B" }` mit `safeLogoBg`
  (Hex `^#[0-9A-Fa-f]{6}$`, sonst `#1E293B`)
- `LanguageSetting { language="de", available=[] }`

### `store.js` — Cache + Queue
Cache-Dateien identisch zum Client: `reasons.json`, `logo.bin` + `logo_meta.json`,
`recent_events.json`, `config.json`. Queue = JSON-Array von `EventIn` unter
`queueFile`; `enqueue` hängt an, `flush(postFn)` postet alle und behält
Fehlschläge. Verhalten 1:1 zu `event_queue.py` / `cache.py`.

### `i18n.js` — `Translator`
Fallback `aktiv → de → key`; Locale-JSON (`de.json`, `en.json`) aus der Extension
gebündelt (Kopie der Client-Locales). Aktive Sprache aus `getSettings().language`,
Default `de`. Key-Parität mit `de.json` per Test erzwungen.

## UI-Parität (`ui/`)

Nachbau des `CardWidget` mit St/Clutter:
- **`overlay.js`** — Vollbild-`St.Widget` (dunkler Hintergrund) pro Monitor,
  zentrierte Karte; Skeleton-/Loading-Zustand während des Ladens; `retranslate()`
  bei Sprachwechsel.
- **`logo.js`** — Logo aus gecachter `logo.bin` als Clutter/St-Image (aus Datei),
  Höhe `logo_height`, Kartenhintergrund `safeLogoBg`.
- Such-`St.Entry` → filtert **`reasonList.js`** (durchsuchbare Grundliste).
- Freitext-`St.Entry` — nur wenn `allow_free_text`.
- **`recentTable.js`** — Recent-Events, begrenzt auf `recent_days`.
- **`footer.js`** — `user@host`, Online/Offline-Indikator, Version aus
  `metadata.json`.
- Button-Row: **Anmelden** (aktiv, sobald Grund **oder** Freitext gewählt) +
  **Abmelden**.
- **`confirmDialog.js`** — St-Modal-Bestätigung für Abmelden, innerhalb des Grabs.

### Async-Loader
Ersetzt den PyQt-`_DataLoader`-Thread durch Soup-async-Aufrufe: erst aus Cache
befüllen (sofort sichtbar, Footer offline), dann `reasons/logo/config/branding/
settings/recent` nachladen, Cache aktualisieren; bei Erfolg Footer online.

## Datenfluss (Submit)

1. Nutzer wählt Grund (Listenauswahl **oder** Freitext) → Anmelden wird aktiv.
2. `EventIn { event_type:"login", host, os_user, reason: gewählt(id|Freitext),
   timestamp: jetzt-ISO }`.
3. `ApiClient.postEvent(evt)` async. Bei Fehler → `store.enqueue(evt)`.
4. `store.flush(postFn)` (versucht ältere Queue-Einträge mitzusenden).
5. `ModalGuard.release()` + Overlay zerstören → Session frei.

## Fehlerbehandlung (Sicherheits-Kernpunkt: fail open)

- **API nicht erreichbar** → Offline-Modus: Cache + Footer offline; Submit bleibt
  möglich (enqueue).
- **`/etc/loginlogbook.env` fehlt/ungültig oder `API_URL` fehlt** → **kein Grab**,
  Fehler ins Journal. Eine fehlkonfigurierte Maschine darf den Nutzer nie
  aussperren.
- **Jede unerwartete Exception in `enable()`** → Grab lösen, Overlay zerstören,
  loggen. Es darf nie ein kaputtes Modal ohne Submit-Weg zurückbleiben.

## Test-Strategie

**Headless mit `gjs` (CI-fähig):**
- `config.js` — env-Parsing (Quotes, Kommentare, Defaults, fehlende Keys).
- `models.js` — Validierung, Hex-Fallback, `event_type`-Enum.
- `store.js` — Cache- und Queue-Roundtrip im tmp-Verzeichnis; `flush` behält
  Fehlschläge.
- `net.js` — mit **gemocktem `Soup.Session`**: prüft URLs, `X-Client-Token`,
  JSON-Parsing, Offline-Fehlerpfad.
- `i18n.js` — Fallback `aktiv → de → key`.
- **Locale-Paritäts-Test** — gleiche Keys wie `de.json` (analog zu den
  bestehenden `test_locale_parity`-Tests).
- `metadata.json` — valides JSON, `uuid` gesetzt, `shell-version` enthält `"50"`.
- Runner: `jasmine-gjs`; Fallback ein minimaler Assert-Runner via `gjs`.

**Nur manuell (kein Live-gnome-shell in CI) — Smoke-Checkliste im README:**
1. Frischer Wayland-Login → Overlay deckt **alle** Monitore.
2. Super / Alt+Tab / Overview / Workspace-Wechsel sind geblockt.
3. Offline-Modus (API gestoppt) → Cache-Daten, Submit enqueued.
4. Anmelden → Grab gelöst, Desktop frei; Event landet in InfluxDB (bzw. Queue).
5. Abmelden → Session terminiert.
6. Multi-Monitor-Layout und `monitors-changed` (Kabel ziehen).
7. **Fehlende/kaputte env → fail-open** (kein Grab, Nutzer kommt normal rein).

## Packaging / Installation

`packaging/install.sh` (Basis für den Installer #20):
- Dateien nach `/usr/share/gnome-shell/extensions/loginlogbook@willeke.tv/`
  (System-Extension für alle Nutzer).
- **Erzwingen per dconf-System-DB:** `enabled-extensions` inkl. UUID in
  `/etc/dconf/db/local.d/` als Default setzen **und** in
  `/etc/dconf/db/local.d/locks/` sperren, sodass Nutzer sie nicht deaktivieren
  können; anschließend `dconf update`.
- Kein gschema-Compile nötig (Config kommt aus env).
- Änderungen greifen beim **nächsten Login** (Wayland lädt die Shell nicht live neu).
- `uninstall.sh` symmetrisch (Dateien entfernen, dconf-Default/Lock zurücknehmen,
  `dconf update`).

## Globale Constraints

- GNOME Shell 50 / gjs 1.88; ESM-Extension; `metadata.json` `shell-version: ["50"]`,
  `uuid: "loginlogbook@willeke.tv"`.
- Nur GJS + `gi://`-Typelibs (`GObject`, `Gio`, `GLib`, `Soup` 3.0, `St`, `Clutter`,
  `Shell`, `Meta`); **keine npm/externen Laufzeit-Deps**.
- **Fail-open**: jede Config-/Startfehler-Situation lässt den Nutzer rein.
- Geteilte env/Cache/Queue mit dem PyQt-Client (gleiche Pfade/Defaults).
- HTTP-Contract identisch zum PyQt-Client (Endpoints, `X-Client-Token`, 5 s Timeout).
- Locale-Parität per Test erzwungen; UI-Texte aus Locale-JSON, keine Hartcodierung.

## Offene Punkte / Risiken

- **VT-Wechsel/Power-Taste** bleiben Restlücken (dokumentiert). Für höhere
  Härtung später logind/PAM erwägen — eigener Spec.
- **GNOME-Update** könnte Extension-APIs brechen; `shell-version` muss bei
  GNOME-Upgrades gepflegt werden. dconf-Lock verhindert Nutzer-Deaktivierung,
  nicht ein hartes API-Break — im Zweifel greift fail-open (kein Grab).
- **Logo-Rendering** aus Bytes: über gecachte Datei laden (Clutter/St-Image),
  um GdkPixbuf-Abhängigkeit zu vermeiden.
