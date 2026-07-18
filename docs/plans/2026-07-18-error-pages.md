# Error-Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Branded, localized error pages across all layers — static nginx pages for infrastructure failures (502/503/504/429) and dynamic i18n HTML error pages from the API — all matching the client overlay look (dark card + embedded LoginLogBook logo).

**Architecture:** nginx serves self-contained static per-language error files (chosen via an `Accept-Language` map) because the API may be down; the API refactors `errors.py` to pull error titles/messages from the API locale files, pick the active language from `settings.json`, and embed the logo as a `data:` URI. Grafana-down is covered by the shared nginx 5xx page.

**Tech Stack:** FastAPI / Starlette exception handlers, nginx `error_page` + `map`, Python 3.13, pytest.

## Global Constraints

- Default/fallback language: `de`. Supported: `de`, `en`. New `error.page.*` keys go in BOTH `app/locales/api/de.json` and `en.json` (parity test enforces identical key sets).
- Look everywhere: dark background `#0F172A`, white card, embedded LoginLogBook logo as a `data:` URI, inline CSS, **no external resources** (CSP-safe), no internal details / version banners.
- nginx error pages are static and self-contained (must work when the API is down). Language via `Accept-Language` (separate `de`/`en` files), `try_files` fallback to `de`.
- API error pages stay HTML only for `Accept: text/html`; API clients keep the existing JSON responses unchanged.
- API page language comes from the server-side setting (`/data/settings.json`), not `Accept-Language`.
- `limit_req_status 429` so the rate limiter returns 429 (→ `@err429`).
- Tests run with `uv run pytest` from inside `loginlogbook-api/` (a `.venv` exists there; do NOT use plain `pytest`/`pip`).

---

## File Structure

**API (Task 1):**
- Modify `loginlogbook-api/app/locales/api/de.json`, `en.json` — add `error.page.*` keys.
- Modify `loginlogbook-api/app/errors.py` — i18n + logo, language from settings.
- Create `loginlogbook-api/tests/test_errors.py`.

**nginx (Task 2):**
- Create `loginlogbook-api/nginx/errors/build_error_pages.py` — author-time generator.
- Create (generated + committed) `loginlogbook-api/nginx/errors/50x.de.html`, `50x.en.html`, `429.de.html`, `429.en.html`.
- Modify `loginlogbook-api/nginx/nginx.conf` and `loginlogbook-api/nginx/nginx.dev.conf`.
- Modify `loginlogbook-api/docker-compose.yml` (add errors mount). `docker-compose.dev.yml` is gitignored — add the same mount locally (not committed).
- Create `loginlogbook-api/tests/test_error_pages_static.py`.

---

## Task 1: API error pages — i18n + logo + visual

**Files:**
- Modify: `loginlogbook-api/app/locales/api/de.json`
- Modify: `loginlogbook-api/app/locales/api/en.json`
- Modify: `loginlogbook-api/app/errors.py`
- Test: `loginlogbook-api/tests/test_errors.py`

**Interfaces:**
- Consumes: `Translator` from `app.i18n` (`t(key, lang, **kwargs)`), `SettingsStore` from `app.settings_store` (`load() -> {"language": ...}`), `get_settings` from `app.config` (`.settings_file`).
- Produces: `register_error_handlers(app)` (unchanged signature) now returning localized, logo-branded HTML.

- [ ] **Step 1: Add the error-page locale keys**

Add to `loginlogbook-api/app/locales/api/de.json` (keep the two existing keys, add these):

```json
{
  "error.logo.none": "Kein Logo gesetzt",
  "error.language.invalid": "Unbekannter Sprachcode",
  "error.page.403.title": "Zugriff verweigert",
  "error.page.403.msg": "Das angegebene Token ist ungültig oder fehlt.",
  "error.page.404.title": "Seite nicht gefunden",
  "error.page.404.msg": "Die angeforderte Ressource existiert nicht.",
  "error.page.405.title": "Methode nicht erlaubt",
  "error.page.405.msg": "Diese HTTP-Methode wird hier nicht unterstützt.",
  "error.page.422.title": "Ungültige Anfrage",
  "error.page.422.msg": "Die Anfrage enthält ungültige oder fehlende Felder.",
  "error.page.500.title": "Interner Fehler",
  "error.page.500.msg": "Ein unerwarteter Fehler ist aufgetreten. Bitte später erneut versuchen.",
  "error.page.generic.title": "Fehler",
  "error.page.generic.msg": "Ein unbekannter Fehler ist aufgetreten.",
  "error.page.back": "← Zur Übersicht"
}
```

Add to `loginlogbook-api/app/locales/api/en.json` (same keys):

```json
{
  "error.logo.none": "No logo set",
  "error.language.invalid": "Unknown language code",
  "error.page.403.title": "Access denied",
  "error.page.403.msg": "The provided token is invalid or missing.",
  "error.page.404.title": "Page not found",
  "error.page.404.msg": "The requested resource does not exist.",
  "error.page.405.title": "Method not allowed",
  "error.page.405.msg": "This HTTP method is not supported here.",
  "error.page.422.title": "Invalid request",
  "error.page.422.msg": "The request contains invalid or missing fields.",
  "error.page.500.title": "Internal error",
  "error.page.500.msg": "An unexpected error occurred. Please try again later.",
  "error.page.generic.title": "Error",
  "error.page.generic.msg": "An unknown error occurred.",
  "error.page.back": "← Back to overview"
}
```

- [ ] **Step 2: Write the failing test**

Create `loginlogbook-api/tests/test_errors.py`:

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client(tmp_path: Path, language: str = "de") -> TestClient:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(f'{{"language": "{language}"}}', encoding="utf-8")
    settings = Settings(admin_token="admintok", client_tokens=["clienttok"],
                        settings_file=settings_file)
    return TestClient(create_app(settings), raise_server_exceptions=False)


def test_html_404_is_localized_german(tmp_path: Path):
    client = _client(tmp_path, "de")
    r = client.get("/does-not-exist", headers={"Accept": "text/html"})
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
    assert "Seite nicht gefunden" in r.text
    assert "data:image/svg+xml;base64," in r.text  # embedded logo


def test_html_404_is_localized_english(tmp_path: Path):
    client = _client(tmp_path, "en")
    r = client.get("/does-not-exist", headers={"Accept": "text/html"})
    assert r.status_code == 404
    assert "Page not found" in r.text


def test_api_client_still_gets_json(tmp_path: Path):
    client = _client(tmp_path, "de")
    r = client.get("/does-not-exist")  # no text/html in Accept
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    assert "detail" in r.json()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_errors.py -v`
Expected: `test_html_404_is_localized_german` / `_english` FAIL (no embedded logo / not localized yet); JSON test may already pass.

- [ ] **Step 4: Refactor errors.py**

Replace the whole `loginlogbook-api/app/errors.py` with:

```python
"""Custom, localized HTML error pages returned to browser clients."""
import base64
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.i18n import Translator
from app.settings_store import SettingsStore

_LOCALES_DIR = Path(__file__).parent / "locales" / "api"
_LOGO_PATH = Path(__file__).parent / "static" / "loginlogbook-logo.svg"
_KNOWN_CODES = (403, 404, 405, 422, 500)
_translator = Translator(_LOCALES_DIR)


def _logo_data_uri() -> str:
    if not _LOGO_PATH.exists():
        return ""
    b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


_LOGO = _logo_data_uri()


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


def _active_language() -> str:
    try:
        return SettingsStore(get_settings().settings_file).load()["language"]
    except Exception:
        return "de"


def _texts(code: int, lang: str) -> tuple[str, str]:
    key = str(code) if code in _KNOWN_CODES else "generic"
    return (
        _translator.t(f"error.page.{key}.title", lang),
        _translator.t(f"error.page.{key}.msg", lang),
    )


def _page(code: int, lang: str) -> str:
    title, message = _texts(code, lang)
    back = _translator.t("error.page.back", lang)
    logo = f'<img class="logo" src="{_LOGO}" alt="LoginLogBook">' if _LOGO else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{code} – LoginLogBook</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #0F172A;
  font-family: "Segoe UI", system-ui, sans-serif;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}}
.card {{
  background: #fff;
  border-radius: 12px;
  padding: 2.5rem 2rem;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.4);
  text-align: center;
}}
.logo {{ height: 56px; margin-bottom: 1.25rem; }}
.code {{ font-size: 4rem; font-weight: 800; color: #E2E8F0; line-height: 1; margin-bottom: 0.75rem; }}
h1 {{ font-size: 1.25rem; font-weight: 700; color: #0F172A; margin-bottom: 0.75rem; }}
p {{ font-size: 0.9375rem; color: #475569; margin-bottom: 1.75rem; line-height: 1.6; }}
a {{ display: inline-block; background: #2563EB; color: #fff; text-decoration: none;
     font-weight: 600; font-size: 0.9375rem; padding: 0.625rem 1.5rem; border-radius: 8px; }}
a:hover {{ background: #1D4ED8; }}
</style>
</head>
<body>
<div class="card">
  {logo}
  <div class="code">{code}</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <a href="/admin">{back}</a>
</div>
</body>
</html>"""


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        return HTMLResponse(content=_page(exc.status_code, _active_language()), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=422, content={"detail": exc.errors()})
        return HTMLResponse(content=_page(422, _active_language()), status_code=422)

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        return HTMLResponse(content=_page(500, _active_language()), status_code=500)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_errors.py tests/test_locale_parity.py -v`
Expected: PASS (3 error tests + parity, which now also checks the new keys exist in both languages).

- [ ] **Step 6: Run the full API suite**

Run: `cd loginlogbook-api && uv run pytest -q`
Expected: all pass (no regressions).

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-api/app/errors.py loginlogbook-api/app/locales/api loginlogbook-api/tests/test_errors.py
git commit -m "feat(errors): localized, logo-branded API error pages"
```

---

## Task 2: nginx static error pages + config + mount

**Files:**
- Create: `loginlogbook-api/nginx/errors/build_error_pages.py`
- Create (generated): `loginlogbook-api/nginx/errors/50x.de.html`, `50x.en.html`, `429.de.html`, `429.en.html`
- Modify: `loginlogbook-api/nginx/nginx.conf`, `loginlogbook-api/nginx/nginx.dev.conf`
- Modify: `loginlogbook-api/docker-compose.yml`
- Test: `loginlogbook-api/tests/test_error_pages_static.py`

**Interfaces:**
- Consumes: the logo at `loginlogbook-api/app/static/loginlogbook-logo.svg`.
- Produces: four static HTML files served by nginx via `@err5xx` / `@err429`.

- [ ] **Step 1: Create the generator**

Create `loginlogbook-api/nginx/errors/build_error_pages.py`:

```python
"""Author-time generator for the static nginx error pages.

Run once and commit the output:  python build_error_pages.py
Produces 50x.<lang>.html and 429.<lang>.html with the LoginLogBook logo
embedded as a data: URI, so the pages are fully self-contained.
"""
import base64
from pathlib import Path

_HERE = Path(__file__).parent
_LOGO_PATH = _HERE.parent.parent / "app" / "static" / "loginlogbook-logo.svg"

_TEXTS = {
    ("50x", "de"): ("Dienst nicht erreichbar",
                    "Der Dienst ist vorübergehend nicht erreichbar. Bitte versuchen Sie es in Kürze erneut.",
                    "Erneut versuchen"),
    ("50x", "en"): ("Service unavailable",
                    "The service is temporarily unavailable. Please try again shortly.",
                    "Try again"),
    ("429", "de"): ("Zu viele Anfragen",
                    "Zu viele Anfragen in kurzer Zeit. Bitte warten Sie einen Moment.",
                    "Erneut versuchen"),
    ("429", "en"): ("Too many requests",
                    "Too many requests in a short time. Please wait a moment.",
                    "Try again"),
}


def _logo_data_uri() -> str:
    b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _render(lang: str, title: str, message: str, retry: str, logo: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} – LoginLogBook</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0F172A; font-family: "Segoe UI", system-ui, sans-serif;
  min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }}
.card {{ background: #fff; border-radius: 12px; padding: 2.5rem 2rem; width: 100%;
  max-width: 480px; box-shadow: 0 24px 64px rgba(0,0,0,0.4); text-align: center; }}
.logo {{ height: 56px; margin-bottom: 1.25rem; }}
h1 {{ font-size: 1.25rem; font-weight: 700; color: #0F172A; margin-bottom: 0.75rem; }}
p {{ font-size: 0.9375rem; color: #475569; margin-bottom: 1.75rem; line-height: 1.6; }}
a {{ display: inline-block; background: #2563EB; color: #fff; text-decoration: none;
     font-weight: 600; font-size: 0.9375rem; padding: 0.625rem 1.5rem; border-radius: 8px; }}
a:hover {{ background: #1D4ED8; }}
</style>
</head>
<body>
<div class="card">
  <img class="logo" src="{logo}" alt="LoginLogBook">
  <h1>{title}</h1>
  <p>{message}</p>
  <a href="/">{retry}</a>
</div>
</body>
</html>"""


def main() -> None:
    logo = _logo_data_uri()
    for (page, lang), (title, message, retry) in _TEXTS.items():
        html = _render(lang, title, message, retry, logo)
        (_HERE / f"{page}.{lang}.html").write_text(html, encoding="utf-8")
    print(f"wrote {len(_TEXTS)} error pages to {_HERE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate the static pages**

Run: `cd loginlogbook-api/nginx/errors && uv run --project ../.. python build_error_pages.py`
Expected: `wrote 4 error pages to .../nginx/errors`, creating `50x.de.html`, `50x.en.html`, `429.de.html`, `429.en.html`.

- [ ] **Step 3: Write the failing static-pages + config test**

Create `loginlogbook-api/tests/test_error_pages_static.py`:

```python
from pathlib import Path

_ROOT = Path(__file__).parent.parent  # loginlogbook-api/
_ERRORS = _ROOT / "nginx" / "errors"


def test_all_error_pages_exist_and_are_self_contained():
    expected = {
        "50x.de.html": "Dienst nicht erreichbar",
        "50x.en.html": "Service unavailable",
        "429.de.html": "Zu viele Anfragen",
        "429.en.html": "Too many requests",
    }
    for name, marker in expected.items():
        html = (_ERRORS / name).read_text(encoding="utf-8")
        assert marker in html
        assert "data:image/svg+xml;base64," in html   # embedded logo
        assert "http://" not in html and "https://" not in html  # no external resources


def test_prod_nginx_config_wires_error_pages():
    conf = (_ROOT / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    assert "map $http_accept_language $err_lang" in conf
    assert "limit_req_status 429;" in conf
    assert "error_page 502 503 504 @err5xx;" in conf
    assert "error_page 429 @err429;" in conf
    assert "location @err5xx" in conf and "location @err429" in conf


def test_dev_nginx_config_wires_5xx_error_page():
    conf = (_ROOT / "nginx" / "nginx.dev.conf").read_text(encoding="utf-8")
    assert "error_page 502 503 504 @err5xx;" in conf
    assert "location @err5xx" in conf
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_error_pages_static.py -v`
Expected: the static-pages test PASSES (files generated in Step 2); the two config tests FAIL (config not wired yet).

- [ ] **Step 5: Wire the prod nginx.conf**

Edit `loginlogbook-api/nginx/nginx.conf`. Add the `map` and `limit_req_status` inside the `http {` block (next to the existing `limit_req_zone`):

```nginx
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
    limit_req_status 429;

    map $http_accept_language $err_lang {
        default    de;
        "~*^en"    en;
    }
```

Inside the `server { listen 443 ssl; ... }` block, after the `add_header` lines and before the `location /grafana/` block, add:

```nginx
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

- [ ] **Step 6: Wire the dev nginx.dev.conf**

Edit `loginlogbook-api/nginx/nginx.dev.conf`. Add inside `http {`:

```nginx
    map $http_accept_language $err_lang {
        default    de;
        "~*^en"    en;
    }
```

Inside its `server { listen 80; ... }` block, before `location /grafana/`, add:

```nginx
        error_page 502 503 504 @err5xx;
        location @err5xx {
            root /etc/nginx/errors;
            try_files /50x.$err_lang.html /50x.de.html =502;
            internal;
        }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_error_pages_static.py -v`
Expected: all 3 pass.

- [ ] **Step 8: Mount the errors dir in compose**

In `loginlogbook-api/docker-compose.yml`, add to the `nginx` service `volumes:` list:

```yaml
      - ./nginx/errors:/etc/nginx/errors:ro
```

Then validate:
```bash
cd loginlogbook-api && cp .env.example .env && docker compose config --quiet && rm -f .env
```
Expected: exit 0, no output.

Also add the same mount line to the local (gitignored) `docker-compose.dev.yml` `nginx` service `volumes:` so dev serves the pages too. This file is not committed.

- [ ] **Step 9: Commit**

```bash
git add loginlogbook-api/nginx/errors/build_error_pages.py \
        loginlogbook-api/nginx/errors/50x.de.html loginlogbook-api/nginx/errors/50x.en.html \
        loginlogbook-api/nginx/errors/429.de.html loginlogbook-api/nginx/errors/429.en.html \
        loginlogbook-api/nginx/nginx.conf loginlogbook-api/nginx/nginx.dev.conf \
        loginlogbook-api/docker-compose.yml \
        loginlogbook-api/tests/test_error_pages_static.py
git commit -m "feat(errors): static nginx error pages with Accept-Language selection"
```

---

## Task 3: Full suites + verification

**Files:** none (verification only).

- [ ] **Step 1: Run the full API suite**

Run: `cd loginlogbook-api && uv run pytest -q`
Expected: all pass (includes `test_errors.py`, `test_error_pages_static.py`, `test_locale_parity.py`).

- [ ] **Step 2: Verify compose still parses**

Run: `cd loginlogbook-api && cp .env.example .env && docker compose config --quiet && rm -f .env`
Expected: exit 0.

- [ ] **Step 3 (optional manual): live smoke**

Stop the API container and hit the site through nginx; expect the branded 50x page (in the browser's language). Trigger the rate limit (>60 req/min) and expect the 429 page. Restart the API.

---

## Self-Review

**Spec coverage:**
- ✅ nginx 502/503/504 + 429 static pages, Accept-Language map, `limit_req_status 429`, `try_files` DE fallback, `internal` locations → Task 2.
- ✅ Compose mount of `errors/` (prod committed; dev local) → Task 2 Step 8.
- ✅ Grafana-down covered by `@err5xx` (shared 5xx page, `/grafana/` proxies through the same server) → Task 2 (no extra work, noted).
- ✅ API pages i18n (keys per code + generic + back) with language from `settings.json` → Task 1.
- ✅ API pages visual rework + embedded logo data-URI → Task 1.
- ✅ JSON responses for API clients unchanged; HTML only on `Accept: text/html` → Task 1 (handlers keep `_wants_html`).
- ✅ Shared dark-card look + embedded logo in both nginx and API pages → Tasks 1 & 2.
- ✅ Key parity for new keys → enforced by existing `test_locale_parity.py`, checked in Task 1 Step 5.
- ✅ No external resources / no version banner / `internal` locations → Task 2 test asserts no `http(s)://`; nginx default banner replaced.
- ✅ Tests: API i18n + JSON fallback (Task 1), static file + config markers (Task 2), full suite + compose (Task 3).

**Notes for the implementer:**
- `raise_server_exceptions=False` on the 500-path test client is required so the `Exception` handler runs instead of the test client re-raising.
- Run the generator (Task 2 Step 2) and commit its output; the pages are static at runtime (no build step in the container).
- `docker-compose.dev.yml` is gitignored — its mount edit stays local and is not part of any commit.
