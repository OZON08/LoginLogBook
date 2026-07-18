# Error-Pages für LoginLogBook — Design

## Ziel

Gebrandete, mehrsprachige Fehlerseiten über alle Ebenen: statische nginx-Seiten für Infrastrukturfehler (Upstream down, Rate-Limit, Timeout) und dynamische, i18n-fähige HTML-Fehlerseiten der API. Look konsistent mit dem Client-Overlay (dunkle Karte + LoginLogBook-Logo). Ersetzt die nginx-Standardseiten und macht die vorhandenen API-Fehlerseiten zweisprachig und optisch stimmig.

## Grundentscheidungen

- **Ebenen:** nginx (502/503/504/429), API-HTML-Fehlerseiten (i18n + Visual), Grafana-Fehler (über die nginx-5xx-Seite abgedeckt).
- **nginx-Seiten:** statisch/self-contained (bei 502 ist die API tot — kein Nachladen von Logo/Branding/Sprache möglich). Sprachwahl per `Accept-Language` (getrennte DE/EN-Dateien).
- **API-Seiten:** dynamisch; Sprache aus der serverseitigen Einstellung (`/data/settings.json`), Texte aus den API-Locales.
- **Look überall:** dunkler Hintergrund `#0F172A`, weiße Karte, eingebettetes LoginLogBook-Logo als `data:`-URI, Inline-CSS, keine externen Ressourcen (CSP-sicher).
- **Default/Fallback-Sprache:** `de`.
- **API-Client-Verhalten unverändert:** HTML nur bei `Accept: text/html`; sonst JSON.

## Ansatz

Statische nginx-Fehlerseiten + i18n-fähige dynamische API-Seiten (Ansatz A). Verworfen: alle Seiten über einen API-Endpoint (scheitert bei 502, weil die API dann tot ist) und eine einzige generische statische Seite (ignoriert i18n/Visual).

## nginx-Ebene

**Statische Dateien** (im nginx-Image gemountet unter `/etc/nginx/errors`, Quelle `loginlogbook-api/nginx/errors/`):

- `50x.de.html`, `50x.en.html` — deckt **502** (API oder Grafana nicht erreichbar), **503** (Wartung), **504** (Timeout): „Dienst vorübergehend nicht erreichbar".
- `429.de.html`, `429.en.html` — Rate-Limit erreicht.

Jede Datei ist self-contained: Inline-CSS, LoginLogBook-Logo als eingebetteter `data:`-URI, dunkle Karte, HTTP-Statuscode und Kurztext.

**nginx-Konfiguration** (in `loginlogbook-api/nginx/nginx.conf`, analog in `nginx.dev.conf`):

```nginx
map $http_accept_language $err_lang {
    default    de;
    "~*^en"    en;
}
...
limit_req_status 429;
...
error_page 502 503 504 @err5xx;
error_page 429 @err429;
location @err5xx {
    root /etc/nginx/errors;
    try_files /50x.$err_lang.html /50x.de.html =502;
    internal;
}
location @err429 {
    root /etc/nginx/errors;
    try_files /429.$err_lang.html /429.de.html =429;
    internal;
}
```

- `limit_req_status 429` sorgt dafür, dass das Rate-Limit 429 (statt Default 503) liefert und so `@err429` trifft.
- Beide Compose-Dateien mounten `./nginx/errors:/etc/nginx/errors:ro`.
- Die Prod-`nginx.conf` behält ihren `limit_req`; die Dev-`nginx.dev.conf` hat kein Rate-Limit, bekommt aber dieselben `error_page`/`@err5xx`-Blöcke (429-Block dort optional, schadet nicht).
- Grafana-down (502 im `/grafana/`-Pfad) nutzt automatisch `@err5xx`. Grafana-interne Fehlerseiten sind nicht beeinflussbar und ausdrücklich außerhalb des Umfangs.

## API-Ebene

`loginlogbook-api/app/errors.py` wird umgebaut:

- Die deutschen Titel/Texte (`_DESCRIPTIONS`) entfallen; stattdessen kommen die Texte aus den API-Locales mit Keys je Statuscode:
  - `error.page.<code>.title` und `error.page.<code>.msg` für 403, 404, 405, 422, 500.
  - `error.page.generic.title` / `error.page.generic.msg` als Fallback für sonstige Codes.
- Sprachwahl: der Handler liest die aktive Sprache aus `settings.json` (über `SettingsStore(get_settings().settings_file)`) und übersetzt via API-`Translator` (`app/locales/api`). Bei Fehlern beim Lesen → `de`.
- `_page(code, title, message)` rendert die dunkle Karte mit eingebettetem Logo-`data:`-URI (gemeinsame Logo-Konstante) und Inline-CSS.
- `_wants_html(request)` bleibt: nur bei `Accept: text/html` HTML, sonst die bestehende JSON-Antwort.
- Die Handler-Registrierung bleibt `register_error_handlers(app)`; die Sprach-/Übersetzer-Auflösung passiert pro Request im Handler.

**Neue Locale-Keys** (in `app/locales/api/de.json` und `en.json`, identische Key-Sets):
`error.page.403.title/msg`, `error.page.404.title/msg`, `error.page.405.title/msg`, `error.page.422.title/msg`, `error.page.500.title/msg`, `error.page.generic.title/msg`. Die deutschen Werte übernehmen die bisherigen `_DESCRIPTIONS`-Texte wortgleich.

## Logo-Asset

Das eingebettete Logo ist eine gemeinsame `data:`-URI-Konstante (aus `app/static/loginlogbook-logo.svg` als Base64/utf8-`data:`-URI). Verwendet sowohl beim Generieren der statischen nginx-Seiten als auch in den API-Seiten, damit der Look identisch ist. Die nginx-`errors/*.html` werden mit dem eingebetteten Logo als fertige statische Dateien committet (kein Build-Schritt zur Laufzeit).

## Fehlerbehandlung / Robustheit

- nginx-Seiten hängen von nichts ab (kein Upstream, keine externen Ressourcen) → funktionieren auch bei komplett toter API.
- `try_files` fällt bei fehlender Sprachdatei auf `50x.de.html` / `429.de.html` zurück, zuletzt auf den nackten Statuscode.
- API-Handler: schlägt das Lesen von `settings.json` oder einer Locale fehl, greift die Fallback-Kette (`aktiv → de → Key`), nie leere Seite, nie zusätzlicher Absturz im Error-Handler.

## Tests

- **API (pytest):**
  - 404/403 mit `Accept: text/html` → Antwort enthält den lokalisierten Titel (DE), Content-Type `text/html`.
  - Sprache = `en` (über die bestehende Settings-Test-Fixture) → englischer Titel/Text.
  - Anfrage ohne `text/html` (API-Client) → weiterhin JSON, unveränderte Struktur.
  - Key-Parität der neuen `error.page.*`-Keys wird vom bestehenden `test_locale_parity.py` miterzwungen.
- **nginx (pytest, dateibasiert):**
  - Die vier `errors/*.html` existieren, sind nicht leer, enthalten den erwarteten Titel je Sprache und den Logo-`data:`-URI-Marker.
  - `nginx.conf` und `nginx.dev.conf` enthalten die `error_page`/`@err5xx`/`@err429`-Blöcke und `limit_req_status 429` (nginx.conf).
- **Compose:** `docker compose config --quiet` bleibt fehlerfrei (Mount der `errors`-Dateien).

## Sicherheit

- Keine externen Ressourcen in den Fehlerseiten (Inline-CSS, eingebettetes Logo) → keine CSP-Verletzung, kein Datenabfluss.
- Fehlerseiten geben keine internen Details preis (keine Stacktraces, keine Versionsbanner — ersetzt u. a. das `nginx/<version>`-Banner der Standardseite).
- `internal;` auf den `@err*`-Locations verhindert direkten externen Aufruf der Fehlerseiten-Pfade.

## Nicht im Umfang (YAGNI)

- Grafana-interne Fehlerseiten (nicht beeinflussbar).
- Fehlerseiten für weitere Statuscodes über die genannten hinaus.
- Live-Branding (konfiguriertes Logo/Farben) auf den Fehlerseiten — es wird das eingebettete Default-Logo genutzt.
- Accept-Language-Auswertung auf den API-Seiten (dort gilt die globale serverseitige Sprache).
