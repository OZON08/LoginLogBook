# i18n / Sprachdateien für LoginLogBook — Design

## Ziel

Alle festen UI-Texte von LoginLogBook aus dem Code in Sprachdateien auslagern und mehrsprachig machen (Deutsch als Standard, Englisch als erste Zusatzsprache). Betrifft: PyQt6-Client, Web-Admin-UI, API-Texte und die Grafana-Dashboards. Das System muss sich mit einer einzigen neuen Datei je Komponente um weitere Sprachen erweitern lassen.

## Grundentscheidungen

- **Sprachen:** Deutsch (`de`, Default/Fallback) + Englisch (`en`). Erweiterbar.
- **Format:** Flache JSON-Schlüssel/Wert-Dateien, ein Format über alle Komponenten.
- **Aktive Sprache:** serverseitige Einstellung in `/data/settings.json`, global für Admin **und** Client.
- **Umschalten:** nur in der Admin-UI (Dropdown). Client folgt der serverseitigen Einstellung.
- **Nicht übersetzt:** Inhaltsdaten (Auswahlgründe, Client-Namen, Freitext) — das sind admin-definierte Daten, keine UI-Beschriftung.
- **Kein Build-Schritt** für Client/Admin/API (reines JSON zur Laufzeit). Grafana nutzt ein Generator-Skript.

## Dateiformat

Flache JSON-Objekte, punkt-getrennter Schlüssel-Namensraum je Bereich:

```json
{
  "client.button.login": "Anmelden",
  "client.footer.online": "Online",
  "admin.tab.clients": "Clients"
}
```

Regeln:
- Schlüssel sind stabil und sprachunabhängig (englische Slugs).
- **Fallback-Kette** im `t()`-Helfer: aktive Sprache → Deutsch (`de`) → der Schlüssel selbst. Nie leere UI.
- Interpolation über benannte Platzhalter `{name}` (z. B. `"recent.days": "Letzte {days} Tage"`).

## Verzeichnisse

Jede Komponente bündelt ihre eigenen Sprachdateien:

- `loginlogbook-client/app/locales/de.json`, `en.json`
- `loginlogbook-api/app/locales/admin/de.json`, `en.json` (für die Admin-UI, per Static ausgeliefert)
- `loginlogbook-api/app/locales/api/de.json`, `en.json` (für API-Texte)
- `loginlogbook-api/app/locales/grafana/de.json`, `en.json` (für den Dashboard-Generator)

Der Satz vorhandener `*.json`-Dateien bestimmt automatisch, welche Sprachen verfügbar sind (`available`).

## Serverseitige Sprach-Einstellung

Neue Datei `/data/settings.json` (analog zum bestehenden `BrandingStore`), verwaltet über einen `SettingsStore` mit atomarem Schreiben und Defaults (`{"language": "de"}`).

Neue Endpoints:
- `GET /settings` — **ohne Auth** (Client und Admin müssen lesen). Antwort:
  `{ "language": "de", "available": ["de", "en"] }`.
  `available` wird zur Laufzeit aus den vorhandenen `admin/*.json`-Dateien abgeleitet (Schnittmenge der Komponenten ist nicht nötig — die Admin-Locales sind die maßgebliche Liste).
- `PUT /settings` — **Admin-Token** (`require_admin`). Body `{ "language": "en" }`. Validiert gegen `available`; ungültiger Code → HTTP 400. Erfolg → 204.

Pydantic-Modell `Settings(language: str)`; Validierung des Codes gegen die vorhandenen Sprachdateien passiert in der Route (nicht im Modell, da dateiabhängig).

## Client (PyQt6)

- Neues Modul `loginlogbook-client/app/i18n.py`: Klasse `Translator` mit
  - `__init__(locales_dir: Path, default: str = "de")` — lädt `de.json` als Basis.
  - `set_language(code: str)` — lädt `<code>.json` und legt sie über die Basis; unbekannter Code → nur Basis.
  - `t(key: str, **kwargs) -> str` — Lookup mit Fallback-Kette und `str.format(**kwargs)`.
  - `available() -> list[str]` — aus Dateinamen.
  - Modulweite Singleton-Instanz + Modulfunktion `t(...)` für bequeme Nutzung in den Widgets.
- **Sprachcode holen:** Der bestehende Daten-Loader (der bereits Config/Branding lädt) ruft zusätzlich `GET /settings` und `translator.set_language(resp.language)`. Bei Erfolg wird ein Signal `language_changed` gefeuert.
- **Widgets:** alle hartcodierten Strings in `app/ui/*.py` durch `t("client...")` ersetzen. Auf `language_changed` bauen die Widgets ihre Texte neu auf (dieselben `set_*`/Neu-Befüllen-Pfade, die schon bei Config-Signalen genutzt werden).
- **Offline:** aktiver Sprachcode wird im lokalen Cache mitgespeichert; beim Start ohne Netz wird der zuletzt bekannte Code genutzt.
- **api_client:** neue Methode `get_settings() -> Settings`.

## Admin-UI (`admin.html`)

- **Texte im HTML** bekommen `data-i18n="admin...."`-Attribute (und `data-i18n-attr` für Platzhaltertexte, z. B. `placeholder`).
- Kleiner JS-Helfer:
  - beim Laden `GET /settings` → aktive Sprache + `available`.
  - lädt `GET /locales/admin/<code>.json` (neuer Static-Endpoint) und `de.json` als Fallback.
  - `applyTranslations()` durchläuft alle `[data-i18n]`-Elemente und setzt Text/Attribut.
- **Sprach-Dropdown** oben, gefüllt aus `available`. Auswahl → `PUT /settings` (mit Admin-Token) → neue Locale laden → `applyTranslations()`. Kein Reload nötig.
- Auslieferung der Admin-Locales: neue Route `GET /locales/admin/{code}.json` (validiert `code` gegen `^[a-z]{2}$`, liefert Datei oder 404). Alternativ Mount als StaticFiles; die explizite Route erlaubt saubere Validierung und ist vorzuziehen.

## API-Texte

- Serverseitiges Modul `loginlogbook-api/app/i18n.py`: `t(key, lang, **kwargs)` mit derselben Fallback-Logik, lädt `locales/api/*.json` (beim Start gecacht).
- Benutzersichtbare Meldungen, die im Response-Body landen, nutzen `t(...)` mit der aktiven Sprache aus `settings.json`. Umfang bewusst klein gehalten (die meisten API-Fehler sind Status-Codes ohne freien Text).

## Grafana (Generator-Skript)

- Dashboards sind provisionierte, statische JSON — **nicht** live pro Sprache umschaltbar.
- Neues Skript `loginlogbook-api/scripts/build_dashboards.py`:
  - liest Dashboard-**Vorlagen** mit `i18n`-Schlüsseln in Titeln/Beschriftungen,
  - ersetzt sie aus `locales/grafana/<lang>.json`,
  - schreibt die fertigen Dashboards nach `grafana/dashboards/` (Prod, 24h) und `grafana/dashboards-dev/` (7d),
  - `lang` als CLI-Argument (Default aus `settings.json`, sonst `de`).
- **Sprachwechsel für Grafana** = Skript neu laufen lassen + `docker compose restart grafana`. Bewusst nicht live.
- Die drei bestehenden Dashboards (Betrieb, Sicherheit, Protokoll) werden auf dieses Vorlagen-Schema umgestellt; die aktuell fest deutschen Panel-Titel wandern in `locales/grafana/de.json`.

## Erweiterbarkeit (neue Sprache)

Eine neue Sprache `xx` hinzufügen:
1. Je Komponente `xx.json` aus `de.json` kopieren und übersetzen:
   `client/app/locales/xx.json`, `api/app/locales/admin/xx.json`, `.../api/xx.json`, `.../grafana/xx.json`.
2. Fertig für Client + Admin + API — `xx` erscheint automatisch im Admin-Dropdown (`available`).
3. Für Grafana: `build_dashboards.py --lang xx` + Grafana-Neustart.

Kein Code-Change, kein Build (außer Grafana-Skriptlauf).

## Fehlerbehandlung

- Fehlender Schlüssel / fehlende Datei → Fallback-Kette, nie Absturz, nie leerer Text.
- `PUT /settings` mit unbekanntem Code → HTTP 400 mit klarer Meldung.
- Client ohne Netz → letzter bekannter Sprachcode aus Cache; Default `de`.
- Ungültiger `code` im Locale-Static-Endpoint → 404 (nach Regex-Validierung, keine Pfad-Traversal-Gefahr).

## Tests

- **Translator/`t()`** (Client + API): Basis-Lookup, Interpolation, Fallback aktive→de→key.
- **`available`-Ableitung**: leitet Sprachliste korrekt aus vorhandenen Dateien ab.
- **`GET`/`PUT /settings`**: Lesen ohne Auth; Schreiben nur mit Admin-Token; ungültiger Code → 400; `PUT` ohne Token → 403.
- **Locale-Static-Endpoint**: gültiger Code liefert JSON; ungültiger/gefährlicher Code → 404/422.
- **Vollständigkeit**: für jede Komponente hat jede Nicht-Default-Sprachdatei **denselben Schlüsselsatz** wie `de.json` (fängt vergessene/übrige Übersetzungen). Dieser Test gilt auch für `en.json`.
- **Grafana-Generator**: erzeugt aus Vorlage + Locale valide Dashboard-JSONs; keine unersetzten `i18n`-Platzhalter im Ergebnis.
- Client-UI wird schlank auf Translator-Ebene getestet, nicht Widget für Widget.

## Sicherheit

- `GET /settings` bewusst ohne Auth (nur Sprachcode + Liste, keine Geheimnisse).
- `PUT /settings` nur mit Admin-Token, `secrets.compare_digest`, Auth-Fehler → 403.
- Locale-Endpoint validiert `code` per Regex `^[a-z]{2}$` gegen Pfad-Traversal.
- Keine externen Ressourcen in der Admin-HTML (Locales kommen von der eigenen API).

## Nicht im Umfang (YAGNI)

- Übersetzung von Inhaltsdaten (Gründe, Client-Namen, Freitext).
- Plural-/Genus-Regeln über einfache `{name}`-Interpolation hinaus.
- Pro-Benutzer-Sprache (die Einstellung ist global).
- Live-Sprachwechsel für Grafana.
