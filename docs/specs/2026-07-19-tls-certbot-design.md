# TLS/HTTPS + optionaler certbot — Design Spec

**Datum:** 2026-07-19
**Status:** Genehmigt (Block 1 + Block 2)
**Komponente:** `loginlogbook-api` (Docker-Compose-Deployment, nginx)

## Ziel

HTTPS-Betrieb von LoginLogBook robust und selbsttragend machen:

1. **Immer ein Zertifikat vorhanden.** nginx startet nie ohne gültige Cert-Dateien — auch beim allerersten `docker compose up` auf einem frischen Host.
2. **Optionale Let's-Encrypt-Automatik.** Wer eine öffentliche Domain hat, aktiviert per Compose-Profil `certbot` echte, automatisch erneuerte Zertifikate. Wer das nicht braucht (internes Deployment), bleibt beim Self-Signed-Cert — ohne Zusatzdienste.

Beide Modi teilen sich **einen** Cert-Pfad. nginx weiß nicht (und muss nicht wissen), woher das Zertifikat stammt.

## Nicht-Ziele (YAGNI)

- Keine Multi-Domain-/Wildcard-Zertifikate. Eine Domain (`TLS_DOMAIN`).
- Kein DNS-01-Challenge-Flow. Nur HTTP-01 über Webroot.
- Keine Zertifikatsverwaltung in der Admin-UI. Alles läuft über Compose + ein Shell-Skript.
- Kein docker-Socket im certbot-Container. Reload läuft über eine nginx-interne Schleife.

## Architektur-Überblick

```
                        ┌──────────────────────────────┐
                        │  ./nginx/certs (bind mount)   │
                        │    server.crt  server.key     │
                        └──────────────────────────────┘
                          ▲ :rw            ▲ :ro
             ┌────────────┘                └──────────────┐
     ┌───────────────┐                            ┌───────────────┐
     │  certs-init   │  legt Self-Signed an,      │    nginx      │
     │ (one-shot)    │  falls Dateien fehlen      │  TLS-Termin.  │
     └───────────────┘                            └───────────────┘
             ▲ läuft VOR nginx                            │ 6h-Reload-Loop
                                                          ▼
     ┌───────────────┐   HTTP-01   ┌──────────────────────────────┐
     │    certbot    │────────────▶│ ./nginx/certbot-webroot      │
     │ profile:certbot│  webroot   │  /.well-known/acme-challenge │
     │ (12h renew)   │  deploy-hook kopiert fullchain→server.crt  │
     └───────────────┘             └──────────────────────────────┘
```

## Block 1 — Selbsttragendes TLS (immer aktiv)

### Einheitlicher Cert-Pfad

nginx liest unverändert:

```
ssl_certificate     /etc/nginx/certs/server.crt;
ssl_certificate_key /etc/nginx/certs/server.key;
```

Diese beiden Dateien sind der einzige Vertrag. Egal ob Self-Signed oder Let's Encrypt — es sind immer genau diese zwei Pfade.

### Bind-Mount `./nginx/certs`

- Bleibt ein Host-Bind-Mount (kein named volume) — Zertifikate sind so für den Admin direkt inspizierbar/austauschbar.
- Ist bereits in `.gitignore` (`nginx/certs/`, `*.crt`, `*.key`, `*.pem`) → wird nie committet. Bestätigt.
- Mount-Rechte:
  - `nginx`: `./nginx/certs:/etc/nginx/certs:ro` (nur lesen)
  - `certs-init`: `./nginx/certs:/etc/nginx/certs:rw` (schreiben, um Self-Signed zu erzeugen)
  - `certbot` (falls aktiv): `./nginx/certs:/etc/nginx/certs:rw` (deploy-hook schreibt hierher)

### `certs-init` Service (Bootstrap)

Ein One-Shot-Container, der **vor** nginx läuft und ein Self-Signed-Cert erzeugt, **nur wenn noch keins existiert**:

- Image: `alpine/openssl` (klein, openssl vorinstalliert) — alternativ `nginx:1.27-alpine` mit `openssl`-Aufruf. **Entscheidung:** `alpine/openssl` für minimale Angriffsfläche, **auf konkrete Version gepinnt** (Repo-Regel „keine unpinned Images"; exakter Tag wird im Plan verifiziert).
- Verhalten: prüft, ob `server.crt` **und** `server.key` existieren. Falls ja → sofort exit 0 (überschreibt **nie** ein bestehendes Zertifikat, auch kein von certbot geschriebenes). Falls nein → erzeugt Self-Signed (RSA 4096, 3650 Tage, `CN=$TLS_DOMAIN`).
- nginx bekommt `depends_on: certs-init: condition: service_completed_successfully`.

Der Self-Signed-Cert ist damit gleichzeitig der **Bootstrap-Cert**, mit dem nginx hochfährt, bevor certbot je gelaufen ist. Das löst das Henne-Ei-Problem (certbot braucht laufendes nginx für die HTTP-01-Challenge, nginx braucht ein Cert zum Starten).

### Neue Env-Variablen (`.env` / `.env.example`)

```
# ── TLS / Domain ──────────────────────────────────────────────
# Domain, unter der LoginLogBook erreichbar ist. Wird als CN ins
# Self-Signed-Cert geschrieben und von certbot als Zertifikatsdomain
# verwendet.
TLS_DOMAIN=loginlogbook.example.com

# ── certbot (optional, nur mit --profile certbot) ─────────────
# E-Mail für Let's-Encrypt-Registrierung und Ablauf-Warnungen.
CERTBOT_EMAIL=admin@example.com
```

`GF_SERVER_ROOT_URL` in `docker-compose.yml` (aktuell hart `https://example.com/grafana/`) wird auf `https://${TLS_DOMAIN}/grafana/` umgestellt, damit Domain nur an einer Stelle gepflegt wird.

## Block 2 — Optionaler certbot (Let's Encrypt, HTTP-01)

### Profil-gesteuerter Service

```yaml
certbot:
  image: certbot/certbot:<pinned-version>   # exakter Tag im Plan verifiziert
  profiles: ["certbot"]
  ...
```

Ohne `--profile certbot` existiert der Dienst nicht → reiner Self-Signed-Betrieb, keine Extra-Container. Mit `docker compose --profile certbot up -d` kommt die Automatik dazu.

### HTTP-01 über gemeinsamen Webroot

- Neuer Bind-Mount `./nginx/certbot-webroot:/var/www/certbot`, geteilt zwischen nginx (`:ro`) und certbot (`:rw`).
- nginx serviert im **HTTP-Server (Port 80)** den ACME-Pfad, **bevor** der HTTPS-Redirect greift:

  ```nginx
  server {
      listen 80;

      location /.well-known/acme-challenge/ {
          root /var/www/certbot;
      }

      location / {
          return 301 https://$host$request_uri;
      }
  }
  ```

  Reihenfolge ist entscheidend: die spezifischere `location /.well-known/acme-challenge/` gewinnt gegen den `/`-Redirect, sodass Let's Encrypt die Challenge-Datei per Klartext-HTTP abholen kann.
- `./nginx/certbot-webroot/` kommt in `.gitignore`.

### Erst-Ausstellung: `scripts/init-letsencrypt.sh`

Ein idempotentes Skript, das die **einmalige** Erst-Beantragung durchführt (Renewals laufen danach automatisch):

1. Prüft, dass `TLS_DOMAIN` und `CERTBOT_EMAIL` gesetzt sind (sonst Abbruch mit Hinweis).
2. Stellt sicher, dass nginx läuft (mit Self-Signed-Bootstrap-Cert), damit die Challenge erreichbar ist.
3. Ruft `certbot certonly --webroot -w /var/www/certbot -d "$TLS_DOMAIN" --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email` auf.
4. Führt den **deploy-hook** aus (siehe unten), der die frisch ausgestellten Dateien in den nginx-Cert-Pfad kopiert und nginx zum Reload bringt.
5. Unterstützt `--staging` (Let's-Encrypt-Staging-Umgebung) als Flag, um Rate-Limits beim Testen zu vermeiden.

### deploy-hook: Zertifikat in den nginx-Pfad kopieren

certbot legt Zertifikate unter `/etc/letsencrypt/live/$TLS_DOMAIN/` ab (eigenes named volume `letsencrypt`). Der deploy-hook kopiert sie in den geteilten Cert-Pfad, den nginx liest:

```
fullchain.pem  →  /etc/nginx/certs/server.crt
privkey.pem    →  /etc/nginx/certs/server.key
```

Dadurch bleibt der nginx-Cert-Pfad die einzige Quelle der Wahrheit; nginx muss die Let's-Encrypt-Verzeichnisstruktur nie kennen. Der Hook wird sowohl bei Erst-Ausstellung als auch bei jedem Renewal ausgeführt.

### Auto-Renewal-Schleife (certbot-Container)

`command` des certbot-Service:

```
trap exit TERM; while :; do certbot renew --deploy-hook "<copy-script>"; sleep 12h & wait $!; done
```

- Alle 12 h `certbot renew` (No-op, solange Cert > 30 Tage gültig — Let's-Encrypt-Standard).
- Bei erfolgreichem Renewal feuert der deploy-hook → Cert-Dateien werden aktualisiert.

### nginx-Reload-Schleife (Prod)

Da der certbot-Container **keinen** docker-Socket bekommt (bewusste Sicherheitsentscheidung), kann er nginx nicht direkt neu laden. Stattdessen lädt sich **nginx selbst** periodisch neu, um erneuerte Cert-Dateien einzulesen. `command` des nginx-Service (nur Prod-Compose):

```
/bin/sh -c "while :; do sleep 6h & wait $!; nginx -s reload; done & nginx -g 'daemon off;'"
```

- Alle 6 h `nginx -s reload` → liest Cert-Dateien neu ein, ohne Verbindungsabbruch.
- Reload ist billig und unschädlich, auch wenn sich nichts geändert hat.
- Dev-Compose (`nginx.dev.conf`, Port 80, kein TLS) bekommt diese Schleife **nicht**.

## Dateien (geplante Änderungen)

| Datei | Art | Zweck |
|---|---|---|
| `docker-compose.yml` | ändern | `certs-init`-Service, `certbot`-Service (Profil), nginx `command`-Reload-Loop, neue Mounts, `depends_on`, `GF_SERVER_ROOT_URL` |
| `nginx/nginx.conf` | ändern | Port-80-Server: ACME-Location vor Redirect |
| `.env.example` | ändern | `TLS_DOMAIN`, `CERTBOT_EMAIL`; TLS-Kommentarblock aktualisieren |
| `scripts/init-letsencrypt.sh` | neu | Erst-Ausstellung + deploy-hook + `--staging` |
| `scripts/deploy-hook.sh` | neu | Kopiert fullchain/privkey → server.crt/server.key (von init + renew genutzt) |
| `.gitignore` | ändern | `nginx/certbot-webroot/` |
| `tests/test_tls_certbot_config.py` | neu | strukturelle Config-Tests |
| `README.md` | ändern | Abschnitt „HTTPS & Zertifikate" (Self-Signed-Default + certbot-Aktivierung + manueller Smoke-Test) |

## Teststrategie

Echte Zertifikatsausstellung ist **nicht** CI-testbar (braucht öffentliche Domain + Let's-Encrypt-Erreichbarkeit). Getestet werden daher **strukturelle Invarianten**:

1. `nginx.conf` enthält die ACME-Location `location /.well-known/acme-challenge/` **vor** dem 301-Redirect.
2. `docker-compose.yml`: `certbot`-Service trägt `profiles: ["certbot"]`; `certs-init` läuft mit `service_completed_successfully` als nginx-`depends_on`.
3. `docker compose config` ist gültig **ohne** Profil (kein certbot-Service sichtbar) **und** mit `--profile certbot` (certbot sichtbar). *(Test überspringt sich selbst, wenn `docker` im CI nicht verfügbar ist.)*
4. `scripts/init-letsencrypt.sh` und `scripts/deploy-hook.sh` existieren und sind ausführbar (`os.access(..., X_OK)`).
5. `.env.example` enthält `TLS_DOMAIN` und `CERTBOT_EMAIL`.

**Manueller Smoke-Test** (dokumentiert in README, nicht automatisiert):
- Frischer Host → `docker compose up -d` → nginx startet mit Self-Signed, HTTPS erreichbar (Browser-Warnung erwartet).
- Mit Domain → `.env` ausfüllen → `docker compose --profile certbot up -d` → `./scripts/init-letsencrypt.sh` → gültiges Let's-Encrypt-Cert, keine Browser-Warnung.

## Offene Risiken / Constraints

- **Kein docker-Zugriff in dieser Umgebung.** `docker compose config`/`nginx -t` kann ich lokal nicht ausführen (User-Rechte). Verifikation der Laufzeit-Config erfolgt durch den User; automatisierte Tests bleiben strukturell.
- **Reload-Latenz:** Ein erneuertes Cert wird erst nach bis zu 6 h aktiv (nginx-Reload-Intervall). Für Let's-Encrypt-Renewals (30-Tage-Vorlauf) unkritisch.
- **Image-Pinning:** Sowohl `certbot/certbot` als auch `alpine/openssl` werden im Plan auf konkrete Versions-Tags gepinnt (Repo-Regel „keine unpinned Images"). Der exakte, aktuell verfügbare Tag wird beim Schreiben des Plans/der Compose-Änderung geprüft.
