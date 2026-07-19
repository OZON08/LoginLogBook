# TLS/HTTPS + optionaler certbot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LoginLogBook fährt immer mit HTTPS hoch (Self-Signed-Bootstrap) und kann per Compose-Profil optional automatische Let's-Encrypt-Zertifikate (HTTP-01) beziehen und erneuern.

**Architecture:** Ein `certs-init`-One-Shot-Container erzeugt vor nginx ein Self-Signed-Cert, falls keins existiert. nginx liest einen einzigen Cert-Pfad (`server.crt`/`server.key`). Ein profil-gesteuerter `certbot`-Container bezieht/erneuert echte Zertifikate über einen geteilten Webroot und kopiert sie per deploy-hook in genau diesen Pfad; nginx lädt sich alle 6 h selbst neu (kein docker-Socket im certbot-Container).

**Tech Stack:** Docker Compose (Profile, `service_completed_successfully`), nginx 1.27-alpine, `alpine/openssl:3.5.7`, `certbot/certbot:v5.7.0`, POSIX-sh-Skripte, pytest + PyYAML für strukturelle Config-Tests.

## Global Constraints

- **Keine unpinned Images.** `alpine/openssl:3.5.7`, `certbot/certbot:v5.7.0` (verifizierte, aktuell verfügbare Tags, Stand 2026-07-19).
- **Ein Cert-Pfad:** nginx liest ausschließlich `/etc/nginx/certs/server.crt` + `/etc/nginx/certs/server.key`. Kein Dienst schreibt woanders hin.
- **Kein docker-Socket im certbot-Container.** Reload läuft über eine nginx-interne 6h-Schleife (nur Prod-Compose, nicht Dev).
- **certs-init überschreibt nie ein bestehendes Cert** (auch kein von certbot geschriebenes).
- **Secrets bleiben ungetrackt:** `nginx/certs/`, `*.crt`, `*.key`, `*.pem`, `.env` sind bereits in `.gitignore`. `nginx/certbot-webroot/` kommt neu dazu.
- **Alle Kommandos aus `loginlogbook-api/` heraus.** Tests: `uv run pytest`. Compose-Datei: `docker-compose.yml`.
- **Commits** enden mit `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## File Structure

| Datei | Verantwortung |
|---|---|
| `scripts/certs-init.sh` | Self-Signed-Bootstrap (nur falls kein Cert da) |
| `scripts/deploy-hook.sh` | Kopiert certbot-Cert → nginx-Cert-Pfad (läuft im certbot-Container) |
| `scripts/init-letsencrypt.sh` | Host-Skript: einmalige Let's-Encrypt-Ausstellung + Reload |
| `nginx/nginx.conf` | Port-80-Server: ACME-Location vor dem HTTPS-Redirect |
| `docker-compose.yml` | `certs-init` + `certbot` Services, nginx-Reload-Loop, Mounts, Volumes, `depends_on` |
| `.env.example` | `TLS_DOMAIN`, `CERTBOT_EMAIL` |
| `.gitignore` | `nginx/certbot-webroot/` |
| `tests/test_tls_certbot_config.py` | strukturelle Config-Tests |
| `README.md` | Abschnitt „HTTPS & Zertifikate" |

Der `tests/test_tls_certbot_config.py` wächst über mehrere Tasks. Gemeinsame Helfer werden in Task 1 angelegt und in Folge-Tasks wiederverwendet.

---

### Task 1: Self-Signed-Bootstrap (`certs-init`) + Env

**Files:**
- Create: `loginlogbook-api/scripts/certs-init.sh`
- Modify: `loginlogbook-api/docker-compose.yml` (neuer `certs-init`-Service; nginx `depends_on`; `GF_SERVER_ROOT_URL`)
- Modify: `loginlogbook-api/.env.example` (TLS-Block)
- Test: `loginlogbook-api/tests/test_tls_certbot_config.py`

**Interfaces:**
- Produces: Service `certs-init` (image `alpine/openssl:3.5.7`), Cert-Pfad `/etc/nginx/certs/server.{crt,key}` befüllt bevor nginx startet. Env-Var `TLS_DOMAIN`. Test-Helfer `_compose()`, `_ROOT`, `_SCRIPTS` für Folge-Tasks.

- [ ] **Step 1: Write the failing test**

Create `loginlogbook-api/tests/test_tls_certbot_config.py`:

```python
"""Structural configuration tests for TLS bootstrap + optional certbot."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parent.parent          # loginlogbook-api/
_COMPOSE = _ROOT / "docker-compose.yml"
_NGINX_CONF = _ROOT / "nginx" / "nginx.conf"
_ENV_EXAMPLE = _ROOT / ".env.example"
_SCRIPTS = _ROOT / "scripts"


def _compose() -> dict:
    return yaml.safe_load(_COMPOSE.read_text(encoding="utf-8"))


def _services() -> dict:
    return _compose()["services"]


def test_env_example_has_tls_domain():
    assert "TLS_DOMAIN" in _ENV_EXAMPLE.read_text(encoding="utf-8")


def test_certs_init_image_pinned():
    assert _services()["certs-init"]["image"] == "alpine/openssl:3.5.7"


def test_nginx_depends_on_certs_init_completed():
    dep = _services()["nginx"]["depends_on"]["certs-init"]
    assert dep["condition"] == "service_completed_successfully"


def test_certs_init_script_executable():
    script = _SCRIPTS / "certs-init.sh"
    assert script.exists()
    assert os.access(script, os.X_OK)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_tls_certbot_config.py -v`
Expected: FAIL — `KeyError: 'certs-init'` / missing script / `TLS_DOMAIN` not found.

- [ ] **Step 3: Create the bootstrap script**

Create `loginlogbook-api/scripts/certs-init.sh`:

```sh
#!/bin/sh
# Bootstrap TLS cert: generate a self-signed pair only if none exists.
# Runs as a one-shot container before nginx starts. Never overwrites an
# existing cert (including one written by certbot).
set -eu

CRT=/etc/nginx/certs/server.crt
KEY=/etc/nginx/certs/server.key

if [ -f "$CRT" ] && [ -f "$KEY" ]; then
    echo "certs-init: $CRT and $KEY already exist — leaving them untouched."
    exit 0
fi

echo "certs-init: generating self-signed certificate for CN=${TLS_DOMAIN:-loginlogbook.local}"
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
    -keyout "$KEY" -out "$CRT" \
    -subj "/CN=${TLS_DOMAIN:-loginlogbook.local}"
echo "certs-init: done."
```

Then make it executable:

```bash
chmod +x loginlogbook-api/scripts/certs-init.sh
```

- [ ] **Step 4: Add the `certs-init` service and wire nginx `depends_on`**

In `loginlogbook-api/docker-compose.yml`, add this service (place it before `nginx`):

```yaml
  certs-init:
    image: alpine/openssl:3.5.7
    env_file: .env
    entrypoint: /bin/sh
    command: -c "/scripts/certs-init.sh"
    volumes:
      - ./nginx/certs:/etc/nginx/certs:rw
      - ./scripts:/scripts:ro
    networks:
      - internal
```

Change the `nginx` service `depends_on` from the list form to the map form with conditions:

```yaml
    depends_on:
      certs-init:
        condition: service_completed_successfully
      api:
        condition: service_started
      grafana:
        condition: service_started
```

Change `GF_SERVER_ROOT_URL` in the `grafana` service from the hard-coded host to the domain variable:

```yaml
      GF_SERVER_ROOT_URL: "https://${TLS_DOMAIN}/grafana/"
```

- [ ] **Step 5: Update `.env.example` TLS block**

In `loginlogbook-api/.env.example`, replace the existing `# ── TLS certificates ──` block with:

```
# ── TLS / Domain ──────────────────────────────────────────────────────────────
# Domain under which LoginLogBook is reachable. Written as the CN of the
# self-signed bootstrap cert and used as the certbot certificate domain.
TLS_DOMAIN=loginlogbook.example.com

# On first start, the `certs-init` container auto-generates a self-signed
# certificate into nginx/certs/ if none exists. For a browser-trusted cert on a
# public domain, enable certbot (see README "HTTPS & Zertifikate"):
#   docker compose --profile certbot up -d
#   ./scripts/init-letsencrypt.sh
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_tls_certbot_config.py -v`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-api/scripts/certs-init.sh loginlogbook-api/docker-compose.yml loginlogbook-api/.env.example loginlogbook-api/tests/test_tls_certbot_config.py
git commit -m "feat(tls): self-signed bootstrap cert via certs-init service

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: ACME-Challenge-Location in nginx

**Files:**
- Modify: `loginlogbook-api/nginx/nginx.conf` (Port-80-Server)
- Modify: `loginlogbook-api/.gitignore` (`nginx/certbot-webroot/`)
- Test: `loginlogbook-api/tests/test_tls_certbot_config.py` (add)

**Interfaces:**
- Consumes: nginx serves `/var/www/certbot` (bind mount added in Task 3).
- Produces: Port-80-Server beantwortet `/.well-known/acme-challenge/` **vor** dem 301-Redirect.

- [ ] **Step 1: Write the failing test**

Append to `loginlogbook-api/tests/test_tls_certbot_config.py`:

```python
def test_acme_location_before_https_redirect():
    conf = _NGINX_CONF.read_text(encoding="utf-8")
    acme = conf.find("/.well-known/acme-challenge/")
    redirect = conf.find("return 301 https://")
    assert acme != -1, "ACME challenge location missing"
    assert redirect != -1, "HTTPS redirect missing"
    assert acme < redirect, "ACME location must come before the HTTPS redirect"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_tls_certbot_config.py::test_acme_location_before_https_redirect -v`
Expected: FAIL — `ACME challenge location missing`.

- [ ] **Step 3: Add the ACME location to the port-80 server**

In `loginlogbook-api/nginx/nginx.conf`, replace the existing port-80 server block:

```nginx
    server {
        listen 80;
        return 301 https://$host$request_uri;
    }
```

with:

```nginx
    server {
        listen 80;

        # Let's Encrypt HTTP-01 challenge — must win over the redirect below.
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }
```

- [ ] **Step 4: Ignore the webroot directory**

Add to `loginlogbook-api/.gitignore` under the `# Secrets / local config` section:

```
nginx/certbot-webroot/
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd loginlogbook-api && uv run pytest tests/test_tls_certbot_config.py::test_acme_location_before_https_redirect -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-api/nginx/nginx.conf loginlogbook-api/.gitignore loginlogbook-api/tests/test_tls_certbot_config.py
git commit -m "feat(tls): serve ACME http-01 challenge before https redirect

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: certbot-Service + deploy-hook + Renewal- und Reload-Schleifen

**Files:**
- Create: `loginlogbook-api/scripts/deploy-hook.sh`
- Modify: `loginlogbook-api/docker-compose.yml` (`certbot`-Service, nginx `command`-Reload-Loop, nginx webroot-Mount, `letsencrypt`-Volume)
- Test: `loginlogbook-api/tests/test_tls_certbot_config.py` (add)

**Interfaces:**
- Consumes: `certs-init` (Task 1), ACME-Location (Task 2), Env `TLS_DOMAIN`, `CERTBOT_EMAIL`.
- Produces: Service `certbot` (image `certbot/certbot:v5.7.0`, `profiles: ["certbot"]`) mit 12h-Renewal-Loop; `deploy-hook.sh` unter `/scripts/deploy-hook.sh` im certbot-Container; nginx-Reload-Loop; named volume `letsencrypt`.

- [ ] **Step 1: Write the failing test**

Append to `loginlogbook-api/tests/test_tls_certbot_config.py`:

```python
def _has_docker() -> bool:
    return shutil.which("docker") is not None


def test_certbot_service_profile_gated():
    assert _services()["certbot"]["profiles"] == ["certbot"]


def test_certbot_image_pinned():
    assert _services()["certbot"]["image"] == "certbot/certbot:v5.7.0"


def test_deploy_hook_script_executable():
    script = _SCRIPTS / "deploy-hook.sh"
    assert script.exists()
    assert os.access(script, os.X_OK)


def test_nginx_has_reload_loop():
    assert "nginx -s reload" in _services()["nginx"]["command"]


def test_letsencrypt_named_volume():
    assert "letsencrypt" in _compose()["volumes"]


@pytest.mark.skipif(not _has_docker(), reason="docker not available")
def test_compose_config_hides_certbot_without_profile():
    env = {**os.environ, "TLS_DOMAIN": "example.com", "CERTBOT_EMAIL": "a@b.c"}
    r = subprocess.run(
        ["docker", "compose", "-f", str(_COMPOSE), "config"],
        capture_output=True, text=True, cwd=_ROOT, env=env,
    )
    assert r.returncode == 0, r.stderr
    cfg = yaml.safe_load(r.stdout)
    assert "certbot" not in cfg["services"]


@pytest.mark.skipif(not _has_docker(), reason="docker not available")
def test_compose_config_shows_certbot_with_profile():
    env = {**os.environ, "TLS_DOMAIN": "example.com", "CERTBOT_EMAIL": "a@b.c"}
    r = subprocess.run(
        ["docker", "compose", "-f", str(_COMPOSE), "--profile", "certbot", "config"],
        capture_output=True, text=True, cwd=_ROOT, env=env,
    )
    assert r.returncode == 0, r.stderr
    cfg = yaml.safe_load(r.stdout)
    assert "certbot" in cfg["services"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_tls_certbot_config.py -v -k "certbot or reload or letsencrypt or deploy_hook"`
Expected: FAIL — `KeyError: 'certbot'` / missing script / no reload loop.

- [ ] **Step 3: Create the deploy-hook script**

Create `loginlogbook-api/scripts/deploy-hook.sh`:

```sh
#!/bin/sh
# certbot deploy-hook: copy the freshly issued/renewed cert into the single
# path nginx reads. Runs INSIDE the certbot container. certbot sets
# RENEWED_LINEAGE to /etc/letsencrypt/live/<domain> for deploy hooks.
set -eu

: "${RENEWED_LINEAGE:?RENEWED_LINEAGE not set — deploy-hook must be run by certbot}"

cp "$RENEWED_LINEAGE/fullchain.pem" /etc/nginx/certs/server.crt
cp "$RENEWED_LINEAGE/privkey.pem"   /etc/nginx/certs/server.key
echo "deploy-hook: copied $RENEWED_LINEAGE -> /etc/nginx/certs/server.{crt,key}"
```

Then:

```bash
chmod +x loginlogbook-api/scripts/deploy-hook.sh
```

- [ ] **Step 4: Add the certbot service**

In `loginlogbook-api/docker-compose.yml`, add (after `nginx`, before the top-level `networks:`):

```yaml
  certbot:
    image: certbot/certbot:v5.7.0
    profiles: ["certbot"]
    restart: unless-stopped
    entrypoint: /bin/sh
    command: -c "trap exit TERM; while :; do certbot renew --deploy-hook /scripts/deploy-hook.sh; sleep 12h & wait $$!; done"
    volumes:
      - letsencrypt:/etc/letsencrypt
      - ./nginx/certbot-webroot:/var/www/certbot
      - ./nginx/certs:/etc/nginx/certs:rw
      - ./scripts:/scripts:ro
    networks:
      - internal
```

Note: `$$!` is Compose's escaping for the shell's `$!` (last background PID). Compose turns `$$` into a literal `$`.

- [ ] **Step 5: Add the nginx reload loop and webroot mount**

In the `nginx` service, add a `command` (right after `restart: unless-stopped`):

```yaml
    command: /bin/sh -c "while :; do sleep 6h & wait $$!; nginx -s reload; done & nginx -g 'daemon off;'"
```

Add the webroot mount to the nginx `volumes` list:

```yaml
      - ./nginx/certbot-webroot:/var/www/certbot:ro
```

- [ ] **Step 6: Add the `letsencrypt` named volume**

In the top-level `volumes:` section of `loginlogbook-api/docker-compose.yml`, add:

```yaml
  letsencrypt:
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_tls_certbot_config.py -v`
Expected: PASS (docker-dependent tests SKIP if docker is unavailable; all others PASS).

- [ ] **Step 8: Commit**

```bash
git add loginlogbook-api/scripts/deploy-hook.sh loginlogbook-api/docker-compose.yml loginlogbook-api/tests/test_tls_certbot_config.py
git commit -m "feat(tls): optional certbot service with renewal and nginx reload loops

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Erst-Ausstellungs-Skript + README

**Files:**
- Create: `loginlogbook-api/scripts/init-letsencrypt.sh`
- Modify: `loginlogbook-api/.env.example` (`CERTBOT_EMAIL`)
- Modify: `README.md` (Abschnitt „HTTPS & Zertifikate")
- Test: `loginlogbook-api/tests/test_tls_certbot_config.py` (add)

**Interfaces:**
- Consumes: `certbot`-Service (Task 3), `deploy-hook.sh` (Task 3), Env `TLS_DOMAIN`, `CERTBOT_EMAIL`.
- Produces: Host-Skript `scripts/init-letsencrypt.sh` (idempotente Erst-Ausstellung, `--staging`-Flag).

- [ ] **Step 1: Write the failing test**

Append to `loginlogbook-api/tests/test_tls_certbot_config.py`:

```python
def test_env_example_has_certbot_email():
    assert "CERTBOT_EMAIL" in _ENV_EXAMPLE.read_text(encoding="utf-8")


def test_init_letsencrypt_executable_and_complete():
    script = _SCRIPTS / "init-letsencrypt.sh"
    assert script.exists()
    assert os.access(script, os.X_OK)
    body = script.read_text(encoding="utf-8")
    assert "certonly" in body
    assert "--webroot" in body
    assert "--deploy-hook" in body
    assert "--staging" in body


def test_readme_documents_https():
    readme = (_ROOT.parent / "README.md").read_text(encoding="utf-8")
    assert "HTTPS & Zertifikate" in readme
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_tls_certbot_config.py -v -k "certbot_email or init_letsencrypt or readme"`
Expected: FAIL — missing script / `CERTBOT_EMAIL` not in `.env.example` / README section missing.

- [ ] **Step 3: Add `CERTBOT_EMAIL` to `.env.example`**

Append to the TLS block in `loginlogbook-api/.env.example` (after the certbot comment):

```
# E-mail for Let's Encrypt registration and expiry warnings (certbot profile).
CERTBOT_EMAIL=admin@example.com
```

- [ ] **Step 4: Create the init script**

Create `loginlogbook-api/scripts/init-letsencrypt.sh`:

```sh
#!/bin/sh
# One-time Let's Encrypt issuance for LoginLogBook.
#
# Prereqs:
#   - stack is up (nginx serving on :80/:443 with the self-signed bootstrap cert)
#   - TLS_DOMAIN and CERTBOT_EMAIL are set in .env
#   - DNS for TLS_DOMAIN points at this host, ports 80/443 reachable
#
# Usage: ./scripts/init-letsencrypt.sh [--staging]
set -eu

cd "$(dirname "$0")/.."

if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

: "${TLS_DOMAIN:?TLS_DOMAIN not set in .env}"
: "${CERTBOT_EMAIL:?CERTBOT_EMAIL not set in .env}"

STAGING=""
if [ "${1:-}" = "--staging" ]; then
    STAGING="--staging"
    echo "init-letsencrypt: using Let's Encrypt STAGING environment"
fi

echo "init-letsencrypt: requesting certificate for $TLS_DOMAIN"
docker compose --profile certbot run --rm --entrypoint certbot certbot \
    certonly --webroot -w /var/www/certbot \
    -d "$TLS_DOMAIN" \
    --email "$CERTBOT_EMAIL" \
    --agree-tos --no-eff-email $STAGING \
    --deploy-hook /scripts/deploy-hook.sh

echo "init-letsencrypt: reloading nginx to pick up the new certificate"
docker compose exec nginx nginx -s reload

echo "init-letsencrypt: done. https://$TLS_DOMAIN should now serve a trusted cert."
```

Then:

```bash
chmod +x loginlogbook-api/scripts/init-letsencrypt.sh
```

- [ ] **Step 5: Document in README**

Add a new section to `README.md` (near the deployment / nginx documentation). Adjust the surrounding heading level to match the existing README structure:

```markdown
## HTTPS & Zertifikate

LoginLogBook terminiert TLS in nginx und liest immer genau ein Zertifikatspaar:
`nginx/certs/server.crt` und `nginx/certs/server.key`.

### Standard: Self-Signed (intern)

Beim ersten `docker compose up -d` erzeugt der `certs-init`-Container ein
selbstsigniertes Zertifikat (CN = `TLS_DOMAIN`), falls noch keins existiert.
nginx startet damit sofort über HTTPS. Browser zeigen eine Zertifikatswarnung –
für interne Deployments erwartet und in Ordnung. Ein vorhandenes Zertifikat wird
nie überschrieben.

### Optional: Let's Encrypt (öffentliche Domain)

Voraussetzungen: öffentliche Domain, DNS zeigt auf den Host, Ports 80/443
erreichbar. In `.env` `TLS_DOMAIN` und `CERTBOT_EMAIL` setzen, dann:

```bash
docker compose --profile certbot up -d       # certbot-Dienst starten
./scripts/init-letsencrypt.sh                 # einmalig ausstellen (+ --staging zum Testen)
```

Der certbot-Container erneuert danach automatisch (alle 12 h Prüfung, Erneuerung
ab 30 Tagen Restlaufzeit) und kopiert das Zertifikat per deploy-hook in den
nginx-Cert-Pfad. nginx lädt sich alle 6 h selbst neu, um erneuerte Zertifikate
einzulesen.

### Manueller Smoke-Test

1. Frischer Host, ohne certbot: `docker compose up -d` → `https://<host>`
   liefert eine Seite mit Zertifikatswarnung (Self-Signed).
2. Mit Domain + certbot: nach `init-letsencrypt.sh` liefert `https://$TLS_DOMAIN`
   ein browservertrautes Zertifikat ohne Warnung.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_tls_certbot_config.py -v`
Expected: PASS (docker-dependent tests may SKIP).

- [ ] **Step 7: Full suite regression check**

Run: `cd loginlogbook-api && uv run pytest -q`
Expected: PASS (no regressions in existing tests).

- [ ] **Step 8: Commit**

```bash
git add loginlogbook-api/scripts/init-letsencrypt.sh loginlogbook-api/.env.example loginlogbook-api/tests/test_tls_certbot_config.py README.md
git commit -m "feat(tls): letsencrypt issuance script and HTTPS docs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Manuelle Verifikation (nach allen Tasks, durch den User — kein docker-Zugriff hier)

1. `docker compose config` (ohne Profil) ist gültig und zeigt keinen `certbot`-Dienst.
2. `docker compose --profile certbot config` zeigt den `certbot`-Dienst.
3. `docker compose up -d` auf frischem Host: nginx startet, `https://<host>` erreichbar (Self-Signed-Warnung).
4. `docker compose exec nginx nginx -t` ist syntaktisch gültig.
5. (Mit Domain) `./scripts/init-letsencrypt.sh --staging` bezieht ein Staging-Cert; danach ohne `--staging` ein echtes.
