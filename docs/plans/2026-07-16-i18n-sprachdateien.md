# i18n / Sprachdateien Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Alle festen UI-Texte von LoginLogBook (Client, Admin-UI, API, Grafana) aus dem Code in JSON-Sprachdateien auslagern und über eine serverseitig gewählte Sprache (DE Standard, EN) mehrsprachig machen.

**Architecture:** Ein einheitliches flaches JSON-Schlüssel/Wert-Format je Komponente mit Fallback-Kette (aktive Sprache → `de` → Key). Die aktive Sprache ist eine serverseitige Einstellung (`/data/settings.json`), gelesen über `GET /settings` (ohne Auth), gesetzt über `PUT /settings` (Admin-Token). Client und Admin-UI holen den Code über die API; Grafana-Dashboards werden per Generator-Skript aus Vorlagen + Locale erzeugt.

**Tech Stack:** Python 3.13 / FastAPI / Pydantic (API), PyQt6 (Client), Vanilla-JS (Admin-UI), InfluxDB/Grafana (Dashboards). Tests mit pytest.

## Global Constraints

- Default- und Fallback-Sprache: `de`. Zusatzsprache: `en`. Weitere Sprachen = neue `xx.json` je Komponente, kein Code-Change.
- Sprachdatei-Format: flaches JSON `{ "namespace.key": "Text" }`, Interpolation über `{name}` mit `str.format` (Python) bzw. Ersatz von `{name}` (JS).
- Fallback-Kette im `t()`: aktive Sprache → `de` → der Schlüssel selbst. Nie leere UI, nie Absturz.
- Aktive Sprache ist **global** (nicht pro Benutzer), gespeichert in `/data/settings.json`.
- `GET /settings` ohne Auth; `PUT /settings` mit Admin-Token (`require_admin`), Auth-Fehler → HTTP 403, ungültiger Sprachcode → HTTP 400.
- `available`-Sprachliste wird zur Laufzeit aus den vorhandenen `app/locales/admin/*.json`-Dateien abgeleitet.
- Locale-Codes werden gegen Regex `^[a-z]{2}$` validiert (Pfad-Traversal-Schutz).
- Inhaltsdaten (Auswahlgründe, Client-Namen, Freitext) werden **nicht** übersetzt.
- Keine externen Ressourcen in `admin.html` (Locales von der eigenen API).
- Token-Vergleiche über `secrets.compare_digest` (bestehendes `require_admin` erledigt das — nicht ändern).
- Tests laufen mit `uv run pytest` aus `loginlogbook-api/` bzw. `loginlogbook-client/`.

---

## File Structure

**API (`loginlogbook-api/`):**
- Create `app/settings_store.py` — file-backed `SettingsStore` (mirror of `branding_store.py`).
- Create `app/i18n.py` — server-side `Translator` + module `t()` for API texts.
- Create `app/locales/api/de.json`, `app/locales/api/en.json` — API texts.
- Create `app/locales/admin/de.json`, `app/locales/admin/en.json` — admin-UI texts.
- Create `app/locales/grafana/de.json`, `app/locales/grafana/en.json` — dashboard labels.
- Create `app/routers/settings.py` — `GET /settings`, `PUT /settings`, `GET /locales/admin/{code}.json`.
- Modify `app/config.py` — add `settings_file: Path`.
- Modify `app/models.py` — add `LanguageSetting` model.
- Modify `app/main.py` — wire `SettingsStore` dependency + include settings router.
- Modify `app/static/admin.html` — `data-i18n` attributes, JS `t()`, language dropdown.
- Create `scripts/build_dashboards.py` — Grafana dashboard generator.
- Create `grafana/templates/*.json` — dashboard templates with `@@key@@` placeholders.

**Client (`loginlogbook-client/`):**
- Create `app/i18n.py` — `Translator` + module `t()`.
- Create `app/locales/de.json`, `app/locales/en.json` — client texts.
- Modify `app/models.py` — add `LanguageSetting`.
- Modify `app/api_client.py` — add `get_settings()`.
- Modify `app/ui/overlay_window.py` — fetch settings, `language_changed` signal, apply.
- Modify `app/ui/*.py` — replace hardcoded strings with `t(...)`.

**Tests:**
- `loginlogbook-api/tests/test_i18n.py`, `test_settings_store.py`, `test_settings_routes.py`, `test_locale_parity.py`, `test_build_dashboards.py`
- `loginlogbook-client/tests/test_i18n.py`, `test_locale_parity.py`

---

## Task 1: API — SettingsStore + config + model

**Files:**
- Create: `loginlogbook-api/app/settings_store.py`
- Modify: `loginlogbook-api/app/config.py`
- Modify: `loginlogbook-api/app/models.py`
- Test: `loginlogbook-api/tests/test_settings_store.py`

**Interfaces:**
- Produces: `SettingsStore(path: Path)` with `load() -> dict` (default `{"language": "de"}`) and `save(data: dict) -> None`; `Settings.settings_file: Path`; Pydantic `LanguageSetting(language: str)`.

- [ ] **Step 1: Write the failing test**

Create `loginlogbook-api/tests/test_settings_store.py`:

```python
from pathlib import Path

from app.settings_store import SettingsStore


def test_load_returns_default_when_missing(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    assert store.load() == {"language": "de"}


def test_save_then_load_roundtrip(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    store.save({"language": "en"})
    assert store.load() == {"language": "en"}


def test_load_merges_defaults(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text("{}", encoding="utf-8")
    assert SettingsStore(path).load() == {"language": "de"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_settings_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.settings_store'`.

- [ ] **Step 3: Create the SettingsStore**

Create `loginlogbook-api/app/settings_store.py`:

```python
"""File-backed storage for global application settings (language, ...)."""
import json
from pathlib import Path

_DEFAULTS: dict = {"language": "de"}


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if not self._path.exists():
            return dict(_DEFAULTS)
        return {**_DEFAULTS, **json.loads(self._path.read_text(encoding="utf-8"))}

    def save(self, data: dict) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self._path)
```

- [ ] **Step 4: Add config path**

In `loginlogbook-api/app/config.py`, add after the `branding_file` line (currently `branding_file: Path = Path("/data/branding.json")`):

```python
    settings_file: Path = Path("/data/settings.json")
```

- [ ] **Step 5: Add the model**

In `loginlogbook-api/app/models.py`, add (imports `Field` already used in that file — reuse existing import; if `from pydantic import ...` lacks `Field`, add it):

```python
class LanguageSetting(BaseModel):
    language: str = Field(default="de", pattern=r"^[a-z]{2}$")
```

Note: `BaseModel` is already imported in `models.py` (used by the existing models). Do not re-import.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_settings_store.py -v`
Expected: PASS (3 passed).

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-api/app/settings_store.py loginlogbook-api/app/config.py loginlogbook-api/app/models.py loginlogbook-api/tests/test_settings_store.py
git commit -m "feat(api): add SettingsStore and language setting model"
```

---

## Task 2: API — server-side i18n helper + API locales

**Files:**
- Create: `loginlogbook-api/app/i18n.py`
- Create: `loginlogbook-api/app/locales/api/de.json`
- Create: `loginlogbook-api/app/locales/api/en.json`
- Test: `loginlogbook-api/tests/test_i18n.py`

**Interfaces:**
- Produces: `Translator(locales_dir: Path, default: str = "de")` with `t(key: str, lang: str, **kwargs) -> str` and `available() -> list[str]`.

- [ ] **Step 1: Write the failing test**

Create `loginlogbook-api/tests/test_i18n.py`:

```python
import json
from pathlib import Path

from app.i18n import Translator


def _write(dir: Path, code: str, data: dict) -> None:
    dir.mkdir(parents=True, exist_ok=True)
    (dir / f"{code}.json").write_text(json.dumps(data), encoding="utf-8")


def test_lookup_active_language(tmp_path: Path):
    _write(tmp_path, "de", {"greet": "Hallo"})
    _write(tmp_path, "en", {"greet": "Hello"})
    tr = Translator(tmp_path)
    assert tr.t("greet", "en") == "Hello"


def test_fallback_to_default_then_key(tmp_path: Path):
    _write(tmp_path, "de", {"only_de": "Nur DE"})
    _write(tmp_path, "en", {})
    tr = Translator(tmp_path)
    assert tr.t("only_de", "en") == "Nur DE"      # falls back to de
    assert tr.t("missing", "en") == "missing"     # falls back to key


def test_interpolation(tmp_path: Path):
    _write(tmp_path, "de", {"days": "Letzte {days} Tage"})
    tr = Translator(tmp_path)
    assert tr.t("days", "de", days=7) == "Letzte 7 Tage"


def test_available_from_files(tmp_path: Path):
    _write(tmp_path, "de", {})
    _write(tmp_path, "en", {})
    assert Translator(tmp_path).available() == ["de", "en"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_i18n.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.i18n'`.

- [ ] **Step 3: Implement the Translator**

Create `loginlogbook-api/app/i18n.py`:

```python
"""Minimal JSON-backed translation helper with a de -> key fallback chain."""
import json
from pathlib import Path


class Translator:
    def __init__(self, locales_dir: Path, default: str = "de") -> None:
        self._dir = locales_dir
        self._default = default
        self._cache: dict[str, dict] = {}

    def _load(self, code: str) -> dict:
        if code not in self._cache:
            path = self._dir / f"{code}.json"
            if path.exists():
                self._cache[code] = json.loads(path.read_text(encoding="utf-8"))
            else:
                self._cache[code] = {}
        return self._cache[code]

    def t(self, key: str, lang: str, **kwargs) -> str:
        text = self._load(lang).get(key)
        if text is None:
            text = self._load(self._default).get(key, key)
        return text.format(**kwargs) if kwargs else text

    def available(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.json"))
```

- [ ] **Step 4: Create the API locale files**

Create `loginlogbook-api/app/locales/api/de.json`:

```json
{
  "error.logo.none": "Kein Logo gesetzt",
  "error.language.invalid": "Unbekannter Sprachcode"
}
```

Create `loginlogbook-api/app/locales/api/en.json`:

```json
{
  "error.logo.none": "No logo set",
  "error.language.invalid": "Unknown language code"
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_i18n.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-api/app/i18n.py loginlogbook-api/app/locales/api loginlogbook-api/tests/test_i18n.py
git commit -m "feat(api): add JSON translator and API locale files"
```

---

## Task 3: API — admin locale files + settings & locale routes + wiring

**Files:**
- Create: `loginlogbook-api/app/locales/admin/de.json`
- Create: `loginlogbook-api/app/locales/admin/en.json`
- Create: `loginlogbook-api/app/routers/settings.py`
- Modify: `loginlogbook-api/app/main.py`
- Test: `loginlogbook-api/tests/test_settings_routes.py`

**Interfaces:**
- Consumes: `SettingsStore` (Task 1), `LanguageSetting` (Task 1), `Translator` (Task 2).
- Produces: `GET /settings` → `{"language": str, "available": list[str]}`; `PUT /settings` (admin) → 204; `GET /locales/admin/{code}.json` → JSON. Dependency provider `get_settings_store()` and `get_admin_translator()` in `app.main`.

- [ ] **Step 1: Write the failing test**

Create `loginlogbook-api/tests/test_settings_routes.py`:

```python
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(admin_token="admintok", client_tokens=["clienttok"],
                        settings_file=tmp_path / "settings.json")
    return TestClient(create_app(settings))


def test_get_settings_no_auth(client: TestClient):
    r = client.get("/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "de"
    assert "de" in body["available"] and "en" in body["available"]


def test_put_settings_requires_admin(client: TestClient):
    r = client.put("/settings", json={"language": "en"})
    assert r.status_code == 403


def test_put_settings_sets_language(client: TestClient):
    r = client.put("/settings", json={"language": "en"},
                   headers={"X-Admin-Token": "admintok"})
    assert r.status_code == 204
    assert client.get("/settings").json()["language"] == "en"


def test_put_settings_rejects_unknown_language(client: TestClient):
    r = client.put("/settings", json={"language": "xx"},
                   headers={"X-Admin-Token": "admintok"})
    assert r.status_code == 400


def test_get_admin_locale(client: TestClient):
    r = client.get("/locales/admin/de.json")
    assert r.status_code == 200
    assert "admin.tab.clients" in r.json()


def test_get_admin_locale_rejects_bad_code(client: TestClient):
    assert client.get("/locales/admin/../secrets.json").status_code == 404
```

- [ ] **Step 2: Create the admin locale files**

Create `loginlogbook-api/app/locales/admin/de.json`:

```json
{
  "admin.title": "LoginLogBook Admin",
  "admin.login.token": "Admin-Token",
  "admin.login.invalid": "Ungültiges Token",
  "admin.login.submit": "Anmelden",
  "admin.logout": "Abmelden",
  "admin.tab.clients": "Clients",
  "admin.tab.reasons": "Auswahlgründe",
  "admin.tab.branding": "Branding",
  "admin.clients.create": "Anlegen",
  "admin.clients.duplicate": "Name bereits vergeben",
  "admin.clients.name": "Name",
  "admin.clients.freetext": "Freitext",
  "admin.branding.nologo": "Kein Logo gesetzt",
  "admin.branding.upload": "Hochladen",
  "admin.branding.formats": "Erlaubte Formate: PNG, SVG · Max. 2 MB",
  "admin.branding.render": "Darstellung im Client",
  "admin.branding.logoheight": "Logo-Höhe (px)",
  "admin.branding.logobg": "Logo-Hintergrund",
  "admin.language": "Sprache"
}
```

Create `loginlogbook-api/app/locales/admin/en.json`:

```json
{
  "admin.title": "LoginLogBook Admin",
  "admin.login.token": "Admin token",
  "admin.login.invalid": "Invalid token",
  "admin.login.submit": "Sign in",
  "admin.logout": "Sign out",
  "admin.tab.clients": "Clients",
  "admin.tab.reasons": "Reasons",
  "admin.tab.branding": "Branding",
  "admin.clients.create": "Create",
  "admin.clients.duplicate": "Name already taken",
  "admin.clients.name": "Name",
  "admin.clients.freetext": "Free text",
  "admin.branding.nologo": "No logo set",
  "admin.branding.upload": "Upload",
  "admin.branding.formats": "Allowed formats: PNG, SVG · Max. 2 MB",
  "admin.branding.render": "Client appearance",
  "admin.branding.logoheight": "Logo height (px)",
  "admin.branding.logobg": "Logo background",
  "admin.language": "Language"
}
```

- [ ] **Step 3: Create the settings router**

Create `loginlogbook-api/app/routers/settings.py`:

```python
"""Global settings (language) and admin-UI locale distribution."""
import json
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth import require_admin
from app.i18n import Translator
from app.models import LanguageSetting
from app.settings_store import SettingsStore

router = APIRouter(tags=["settings"])

_CODE_RE = re.compile(r"^[a-z]{2}$")
_ADMIN_LOCALES = Path(__file__).parent.parent / "locales" / "admin"


def get_settings_store() -> SettingsStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


def get_admin_translator() -> Translator:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("/settings")
def get_app_settings(
    store: Annotated[SettingsStore, Depends(get_settings_store)],
    translator: Annotated[Translator, Depends(get_admin_translator)],
) -> dict:
    return {"language": store.load()["language"], "available": translator.available()}


@router.put(
    "/settings",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def put_app_settings(
    setting: LanguageSetting,
    store: Annotated[SettingsStore, Depends(get_settings_store)],
    translator: Annotated[Translator, Depends(get_admin_translator)],
) -> None:
    if setting.language not in translator.available():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unknown language code")
    store.save({"language": setting.language})


@router.get("/locales/admin/{code}.json")
def get_admin_locale(code: str) -> Response:
    if not _CODE_RE.match(code):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    path = _ADMIN_LOCALES / f"{code}.json"
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return Response(content=path.read_text(encoding="utf-8"),
                    media_type="application/json")
```

Note: `{code}.json` in the path matches the literal `.json` suffix; FastAPI binds `code` to the part before `.json`. A traversal attempt like `../secrets.json` does not match `^[a-z]{2}$` and returns 404.

- [ ] **Step 4: Wire into main.py**

In `loginlogbook-api/app/main.py`:

Add imports near the other router imports:

```python
from app.routers import settings as settings_router
from app.settings_store import SettingsStore
from app.i18n import Translator
```

Add a module constant near `_STATIC_DIR`:

```python
_ADMIN_LOCALES_DIR = Path(__file__).parent / "locales" / "admin"
```

Add provider functions near `get_branding_store`:

```python
def get_settings_store() -> SettingsStore:
    return SettingsStore(get_settings().settings_file)


def get_admin_translator() -> Translator:
    return Translator(_ADMIN_LOCALES_DIR)
```

In `create_app`, after `app.include_router(admin_router.router)`:

```python
    app.include_router(settings_router.router)
```

After the existing `app.dependency_overrides[...]` block, add:

```python
    app.dependency_overrides[settings_router.get_settings_store] = get_settings_store
    app.dependency_overrides[settings_router.get_admin_translator] = get_admin_translator
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_settings_routes.py -v`
Expected: PASS (6 passed).

- [ ] **Step 6: Run the full API suite (no regressions)**

Run: `cd loginlogbook-api && uv run pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-api/app/locales/admin loginlogbook-api/app/routers/settings.py loginlogbook-api/app/main.py loginlogbook-api/tests/test_settings_routes.py
git commit -m "feat(api): add /settings and admin locale endpoints"
```

---

## Task 4: Admin-UI — data-i18n, JS t(), language dropdown

**Files:**
- Modify: `loginlogbook-api/app/static/admin.html`

**Interfaces:**
- Consumes: `GET /settings`, `PUT /settings`, `GET /locales/admin/{code}.json` (Task 3).
- Produces: no code interface; a working language switch in the admin UI.

- [ ] **Step 1: Read the current admin.html**

Run: `sed -n '1,400p' loginlogbook-api/app/static/admin.html` — locate the visible German strings (tabs "Clients"/"Auswahlgründe"/"Branding", buttons "Anmelden"/"Abmelden"/"Anlegen"/"Hochladen", labels).

- [ ] **Step 2: Add `data-i18n` attributes**

For each visible text element, add a `data-i18n` attribute with the matching key from `admin/de.json` (Task 3) and keep the German text as the in-HTML fallback. Examples (apply the same pattern to every labelled element):

```html
<button id="login-btn" data-i18n="admin.login.submit">Anmelden</button>
<button id="logout-btn" data-i18n="admin.logout">Abmelden</button>
<button data-i18n="admin.tab.clients">Clients</button>
<button data-i18n="admin.tab.reasons">Auswahlgründe</button>
<button data-i18n="admin.tab.branding">Branding</button>
```

For placeholder / attribute texts use `data-i18n-attr` naming the attribute, e.g.:

```html
<input id="client-name" data-i18n-attr="placeholder:admin.clients.name" placeholder="Name">
```

- [ ] **Step 3: Add the language dropdown**

Next to the logout button, add:

```html
<select id="lang-select" aria-label="Sprache"></select>
```

- [ ] **Step 4: Add the i18n JS**

In the page's `<script>`, add (self-contained, no external libs):

```javascript
const i18n = { dict: {}, fallback: {} };

function t(key) {
  return i18n.dict[key] ?? i18n.fallback[key] ?? key;
}

async function loadLocale(code) {
  i18n.fallback = await (await fetch('/locales/admin/de.json')).json();
  i18n.dict = code === 'de'
    ? i18n.fallback
    : await (await fetch('/locales/admin/' + code + '.json')).json();
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.getAttribute('data-i18n'));
  });
  document.querySelectorAll('[data-i18n-attr]').forEach(el => {
    const [attr, key] = el.getAttribute('data-i18n-attr').split(':');
    el.setAttribute(attr, t(key));
  });
}

async function initI18n() {
  const s = await (await fetch('/settings')).json();
  const sel = document.getElementById('lang-select');
  sel.innerHTML = s.available.map(c =>
    `<option value="${c}"${c === s.language ? ' selected' : ''}>${c.toUpperCase()}</option>`
  ).join('');
  await loadLocale(s.language);
  applyTranslations();
  sel.addEventListener('change', async () => {
    await fetch('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': adminToken },
      body: JSON.stringify({ language: sel.value }),
    });
    await loadLocale(sel.value);
    applyTranslations();
  });
}
```

Call `initI18n()` after a successful admin login (where `adminToken` is already available in the existing script — reuse the existing variable holding the admin token; do not introduce a new storage mechanism).

- [ ] **Step 5: Manual verification**

Rebuild/restart the API, open `/admin`, log in. Expected: dropdown shows `DE`/`EN`; switching to `EN` relabels tabs/buttons live and persists after reload (because `GET /settings` returns `en`).

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-api/app/static/admin.html
git commit -m "feat(admin): language switcher and data-i18n labels"
```

---

## Task 5: Client — i18n Translator + client locale files

**Files:**
- Create: `loginlogbook-client/app/i18n.py`
- Create: `loginlogbook-client/app/locales/de.json`
- Create: `loginlogbook-client/app/locales/en.json`
- Test: `loginlogbook-client/tests/test_i18n.py`

**Interfaces:**
- Produces: module-level `set_language(code: str)`, `t(key: str, **kwargs) -> str`, `available() -> list[str]`, backed by a `Translator` singleton reading `app/locales/`.

- [ ] **Step 1: Write the failing test**

Create `loginlogbook-client/tests/test_i18n.py`:

```python
from app import i18n


def test_default_is_german():
    i18n.set_language("de")
    assert i18n.t("client.button.login") == "Anmelden"


def test_switch_to_english():
    i18n.set_language("en")
    assert i18n.t("client.button.login") == "Sign in"
    i18n.set_language("de")  # reset for other tests


def test_fallback_to_default_then_key():
    i18n.set_language("en")
    assert i18n.t("does.not.exist") == "does.not.exist"
    i18n.set_language("de")


def test_interpolation():
    i18n.set_language("de")
    assert i18n.t("client.recent.days", days=7) == "Letzte 7 Tage"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-client && uv run pytest tests/test_i18n.py -v`
Expected: FAIL with `ModuleNotFoundError` / missing keys.

- [ ] **Step 3: Implement the client i18n module**

Create `loginlogbook-client/app/i18n.py`:

```python
"""Client-side translation helper with active -> de -> key fallback."""
import json
from pathlib import Path

_LOCALES = Path(__file__).parent / "locales"
_DEFAULT = "de"


class Translator:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self._active = _DEFAULT

    def _load(self, code: str) -> dict:
        if code not in self._cache:
            path = _LOCALES / f"{code}.json"
            self._cache[code] = (
                json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            )
        return self._cache[code]

    def set_language(self, code: str) -> None:
        self._active = code

    def t(self, key: str, **kwargs) -> str:
        text = self._load(self._active).get(key)
        if text is None:
            text = self._load(_DEFAULT).get(key, key)
        return text.format(**kwargs) if kwargs else text

    def available(self) -> list[str]:
        return sorted(p.stem for p in _LOCALES.glob("*.json"))


_translator = Translator()
set_language = _translator.set_language
t = _translator.t
available = _translator.available
```

- [ ] **Step 4: Create the client locale files**

Create `loginlogbook-client/app/locales/de.json`:

```json
{
  "client.button.login": "Anmelden",
  "client.button.logout": "Abmelden",
  "client.button.logout.noreason": "Abmelden ohne Anmeldungsgrund",
  "client.reason.select": "Anmeldegrund auswählen",
  "client.reason.search": "Anmeldegrund suchen",
  "client.reason.search.placeholder": "Grund suchen…",
  "client.reason.label": "Grund",
  "client.freetext.label": "Freitext-Eingabe",
  "client.freetext.placeholder": "Freitext eingeben …",
  "client.freetext.none": "Es wird kein Anmeldungsgrund erfasst.",
  "client.confirm.logout.title": "Abmelden bestätigen",
  "client.confirm.cancel": "Abbrechen",
  "client.recent.title": "Letzte Anmeldungen",
  "client.recent.empty": "Keine Anmeldungen in diesem Zeitraum",
  "client.recent.days": "Letzte {days} Tage",
  "client.recent.col.datetime": "Datum / Uhrzeit",
  "client.recent.col.user": "Benutzer",
  "client.recent.col.reason": "Grund",
  "client.recent.table.a11y": "Tabelle der letzten Anmeldungen",
  "client.footer.online": "Online",
  "client.footer.offline": "Offline – Cache",
  "client.footer.user.a11y": "Angemeldeter Benutzer und Hostname",
  "client.logo.a11y": "Firmenlogo"
}
```

Create `loginlogbook-client/app/locales/en.json`:

```json
{
  "client.button.login": "Sign in",
  "client.button.logout": "Sign out",
  "client.button.logout.noreason": "Sign out without a reason",
  "client.reason.select": "Select a login reason",
  "client.reason.search": "Search login reason",
  "client.reason.search.placeholder": "Search reason…",
  "client.reason.label": "Reason",
  "client.freetext.label": "Free-text entry",
  "client.freetext.placeholder": "Enter free text …",
  "client.freetext.none": "No login reason will be recorded.",
  "client.confirm.logout.title": "Confirm sign out",
  "client.confirm.cancel": "Cancel",
  "client.recent.title": "Recent logins",
  "client.recent.empty": "No logins in this period",
  "client.recent.days": "Last {days} days",
  "client.recent.col.datetime": "Date / time",
  "client.recent.col.user": "User",
  "client.recent.col.reason": "Reason",
  "client.recent.table.a11y": "Table of recent logins",
  "client.footer.online": "Online",
  "client.footer.offline": "Offline – cache",
  "client.footer.user.a11y": "Signed-in user and hostname",
  "client.logo.a11y": "Company logo"
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd loginlogbook-client && uv run pytest tests/test_i18n.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add loginlogbook-client/app/i18n.py loginlogbook-client/app/locales loginlogbook-client/tests/test_i18n.py
git commit -m "feat(client): add translator and client locale files"
```

---

## Task 6: Client — fetch language via API + language_changed signal

**Files:**
- Modify: `loginlogbook-client/app/models.py`
- Modify: `loginlogbook-client/app/api_client.py`
- Modify: `loginlogbook-client/app/ui/overlay_window.py`
- Test: `loginlogbook-client/tests/test_api_client_settings.py`

**Interfaces:**
- Consumes: `GET /settings` (Task 3); `i18n.set_language` (Task 5).
- Produces: `LanguageSetting(language: str, available: list[str])` model; `ApiClient.get_settings() -> LanguageSetting`; `overlay` fetches settings and emits `language_changed = pyqtSignal(str)`.

- [ ] **Step 1: Write the failing test**

Create `loginlogbook-client/tests/test_api_client_settings.py`:

```python
from app.api_client import ApiClient
from app.models import LanguageSetting


class _FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def test_get_settings_parses(monkeypatch):
    client = ApiClient(base_url="http://x", token="t")

    def fake_get(url, **kw):
        assert url.endswith("/settings")
        return _FakeResp({"language": "en", "available": ["de", "en"]})

    monkeypatch.setattr(client._session, "get", fake_get)
    result = client.get_settings()
    assert isinstance(result, LanguageSetting)
    assert result.language == "en"
    assert result.available == ["de", "en"]
```

Note: match the existing `ApiClient` constructor/session attribute names when you open the file — if the session attribute is named differently than `_session`, adjust the monkeypatch target and this note accordingly, keeping the same behaviour.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-client && uv run pytest tests/test_api_client_settings.py -v`
Expected: FAIL (`get_settings` / `LanguageSetting` missing).

- [ ] **Step 3: Add the model**

In `loginlogbook-client/app/models.py`, add (mirror the existing model style in that file; it already uses `pydantic` `BaseModel`):

```python
class LanguageSetting(BaseModel):
    language: str = "de"
    available: list[str] = []
```

- [ ] **Step 4: Add the api_client method**

In `loginlogbook-client/app/api_client.py`, add a method mirroring the existing `get_branding_config()` GET pattern already in that file:

```python
    def get_settings(self) -> LanguageSetting:
        resp = self._session.get(f"{self._base_url}/settings", timeout=self._timeout)
        resp.raise_for_status()
        return LanguageSetting(**resp.json())
```

Import `LanguageSetting` at the top (extend the existing `from app.models import ...` line). Use the exact base-URL / session / timeout attribute names already used by `get_branding_config` in this file.

- [ ] **Step 5: Wire into the overlay loader**

In `loginlogbook-client/app/ui/overlay_window.py`:
- Add a signal on the window class: `language_changed = pyqtSignal(str)`.
- In the `_DataLoader.run()` method (which already fetches config and branding), add a settings fetch guarded by its own try/except so a failure never blocks other data:

```python
        try:
            settings = self._api.get_settings()
            self.settings_loaded.emit(settings)
        except Exception:
            pass
```

and add `settings_loaded = pyqtSignal(object)` to the loader.
- Add a handler on the window that applies the language and notifies widgets:

```python
    def _on_settings(self, s: "LanguageSetting") -> None:
        from app import i18n
        i18n.set_language(s.language)
        self.language_changed.emit(s.language)
```

- Connect `loader.settings_loaded` to `self._on_settings`. Import `LanguageSetting` for the type hint.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd loginlogbook-client && uv run pytest tests/test_api_client_settings.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add loginlogbook-client/app/models.py loginlogbook-client/app/api_client.py loginlogbook-client/app/ui/overlay_window.py loginlogbook-client/tests/test_api_client_settings.py
git commit -m "feat(client): fetch active language from API and broadcast language_changed"
```

---

## Task 7: Client — replace hardcoded strings and rebuild on language change

**Files:**
- Modify: `loginlogbook-client/app/ui/button_row.py`
- Modify: `loginlogbook-client/app/ui/reason_list.py`
- Modify: `loginlogbook-client/app/ui/search_field.py`
- Modify: `loginlogbook-client/app/ui/confirm_dialog.py`
- Modify: `loginlogbook-client/app/ui/recent_table.py`
- Modify: `loginlogbook-client/app/ui/footer_bar.py`
- Modify: `loginlogbook-client/app/ui/card_widget.py`
- Modify: `loginlogbook-client/app/ui/logo_widget.py`
- Modify: `loginlogbook-client/app/ui/overlay_window.py`

**Interfaces:**
- Consumes: `i18n.t` (Task 5), `window.language_changed` (Task 6).

- [ ] **Step 1: Replace strings with `t()` calls**

In each widget file, `from app.i18n import t` and replace every hardcoded German user-facing string (labels, button text, placeholders, `setAccessibleName`, empty-state text, column headers) with the matching key from `client/locales/de.json` (Task 5). Reference table (string → key):

| German string | Key |
|---|---|
| `Anmelden` | `client.button.login` |
| `Abmelden` | `client.button.logout` |
| `Abmelden ohne Anmeldungsgrund` | `client.button.logout.noreason` |
| `Anmeldegrund auswählen` | `client.reason.select` |
| `Anmeldegrund suchen` | `client.reason.search` |
| `Grund suchen…` | `client.reason.search.placeholder` |
| `Grund` | `client.reason.label` |
| `Freitext-Eingabe` | `client.freetext.label` |
| `Freitext eingeben …` | `client.freetext.placeholder` |
| `Es wird kein Anmeldungsgrund erfasst.` | `client.freetext.none` |
| `Abmelden bestätigen` | `client.confirm.logout.title` |
| `Abbrechen` | `client.confirm.cancel` |
| `Letzte Anmeldungen` | `client.recent.title` |
| `Keine Anmeldungen in diesem Zeitraum` | `client.recent.empty` |
| `Letzte {days} Tage` | `client.recent.days` (call `t("client.recent.days", days=n)`) |
| `Datum / Uhrzeit` | `client.recent.col.datetime` |
| `Benutzer` | `client.recent.col.user` |
| `Tabelle der letzten Anmeldungen` | `client.recent.table.a11y` |
| `Online` | `client.footer.online` |
| `Offline – Cache` | `client.footer.offline` |
| `Angemeldeter Benutzer und Hostname` | `client.footer.user.a11y` |
| `Firmenlogo` | `client.logo.a11y` |

Leave `LoginLogBook` (product name) and the license/version line untranslated. Non-user-facing docstrings/comments stay as they are.

- [ ] **Step 2: Add a `retranslate()` per widget and connect it**

Give each widget that shows text a `retranslate()` method that re-applies its `t()` strings (move the `t()` calls from `__init__` into `retranslate()` and call it from `__init__`). In `overlay_window.py`, connect `self.language_changed` to each child widget's `retranslate` so a language change re-labels the live UI:

```python
        self.language_changed.connect(lambda _code: self._retranslate_all())
```

where `_retranslate_all()` calls `retranslate()` on the card, button row, reason list, search field, recent table and footer. Widgets that rebuild fully on config/data signals (e.g. the recent table repopulated via its existing `populate()`) only need their static labels/headers re-applied.

- [ ] **Step 3: Verify the client still imports and constructs**

Run: `cd loginlogbook-client && uv run pytest -q`
Expected: all existing tests pass (no import errors, widgets construct).

- [ ] **Step 4: Manual smoke (optional if a display is available)**

Run the client against a dev API whose `/settings` returns `en`; expected: buttons/labels render in English. Switching the language in the admin UI and restarting the client shows the new language.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-client/app/ui
git commit -m "feat(client): render UI text via i18n and retranslate on language change"
```

---

## Task 8: Grafana — locale files + dashboard generator + templated dashboards

**Files:**
- Create: `loginlogbook-api/app/locales/grafana/de.json`
- Create: `loginlogbook-api/app/locales/grafana/en.json`
- Create: `loginlogbook-api/scripts/build_dashboards.py`
- Create: `loginlogbook-api/grafana/templates/loginlogbook-betrieb.json`
- Create: `loginlogbook-api/grafana/templates/loginlogbook-sicherheit.json`
- Create: `loginlogbook-api/grafana/templates/loginlogbook-protokoll.json`
- Test: `loginlogbook-api/tests/test_build_dashboards.py`

**Interfaces:**
- Consumes: `Translator` (Task 2) reading `locales/grafana`.
- Produces: `build_dashboards.py` writing `grafana/dashboards/*.json` (24h) and `grafana/dashboards-dev/*.json` (7d) with all `@@key@@` placeholders replaced.

- [ ] **Step 1: Create the templates**

Copy each current dashboard from `loginlogbook-api/grafana/dashboards/` to `grafana/templates/` and replace every human-facing title/label string with a `@@grafana.<key>@@` placeholder. Example (Betrieb): panel title `"Logins gesamt"` → `"@@grafana.betrieb.total@@"`, dashboard `"title": "LoginLogBook – Betrieb"` → `"@@grafana.betrieb.dashtitle@@"`. Do **not** placeholder Flux queries, uids, or field names — only display text.

- [ ] **Step 2: Create the Grafana locale files**

Create `loginlogbook-api/app/locales/grafana/de.json` (keys for every placeholder used, German values matching the current dashboards):

```json
{
  "grafana.betrieb.dashtitle": "LoginLogBook – Betrieb",
  "grafana.betrieb.total": "Logins gesamt",
  "grafana.betrieb.clients": "Aktive Clients",
  "grafana.betrieb.users": "Aktive Benutzer",
  "grafana.betrieb.overtime": "Anmeldungen über Zeit",
  "grafana.betrieb.topclients": "Top-Clients",
  "grafana.betrieb.reasons": "Anmeldegründe",
  "grafana.sicher.dashtitle": "LoginLogBook – Sicherheit",
  "grafana.sicher.byhour": "Anmeldungen nach Tageszeit (Stunde)",
  "grafana.sicher.offhours": "Außerhalb Geschäftszeiten",
  "grafana.sicher.noreason": "Logins ohne Grund",
  "grafana.sicher.loginlogout": "Login vs. Logout",
  "grafana.proto.dashtitle": "LoginLogBook – Protokoll",
  "grafana.proto.table": "Alle Anmeldungen",
  "grafana.col.time": "Zeit",
  "grafana.col.client": "Client",
  "grafana.col.user": "Benutzer",
  "grafana.col.type": "Typ",
  "grafana.col.reason": "Grund"
}
```

Create `loginlogbook-api/app/locales/grafana/en.json` with the same keys and English values (e.g. `"grafana.betrieb.total": "Total logins"`, `"grafana.col.time": "Time"`, etc.). Every key present in `de.json` MUST exist here.

- [ ] **Step 3: Write the failing test**

Create `loginlogbook-api/tests/test_build_dashboards.py`:

```python
import json
from pathlib import Path

from scripts.build_dashboards import render_dashboard


def test_render_replaces_placeholders(tmp_path: Path):
    template = {"title": "@@grafana.betrieb.dashtitle@@",
                "panels": [{"title": "@@grafana.betrieb.total@@"}]}
    locale = {"grafana.betrieb.dashtitle": "LoginLogBook – Betrieb",
              "grafana.betrieb.total": "Logins gesamt"}
    out = render_dashboard(template, locale)
    assert out["title"] == "LoginLogBook – Betrieb"
    assert out["panels"][0]["title"] == "Logins gesamt"
    assert "@@" not in json.dumps(out)


def test_render_missing_key_raises(tmp_path: Path):
    template = {"title": "@@grafana.unknown@@"}
    import pytest
    with pytest.raises(KeyError):
        render_dashboard(template, {})
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd loginlogbook-api && uv run pytest tests/test_build_dashboards.py -v`
Expected: FAIL (`scripts.build_dashboards` missing).

- [ ] **Step 5: Implement the generator**

Create `loginlogbook-api/scripts/build_dashboards.py`:

```python
"""Generate Grafana dashboards from templates + grafana locale files.

Usage: python -m scripts.build_dashboards [--lang de]
Replaces @@grafana.key@@ placeholders with the locale value. Writes 24h
variants to grafana/dashboards/ and 7d variants to grafana/dashboards-dev/.
"""
import argparse
import json
import re
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_TEMPLATES = _ROOT / "grafana" / "templates"
_LOCALES = _ROOT / "app" / "locales" / "grafana"
_PROD = _ROOT / "grafana" / "dashboards"
_DEV = _ROOT / "grafana" / "dashboards-dev"
_PLACEHOLDER = re.compile(r"@@([a-z0-9._]+)@@")


def render_dashboard(template: dict, locale: dict) -> dict:
    def sub(m: re.Match) -> str:
        return locale[m.group(1)]  # KeyError on missing key = fail loud
    text = _PLACEHOLDER.sub(sub, json.dumps(template, ensure_ascii=False))
    return json.loads(text)


def _load_locale(lang: str) -> dict:
    base = json.loads((_LOCALES / "de.json").read_text(encoding="utf-8"))
    if lang != "de":
        base = {**base, **json.loads((_LOCALES / f"{lang}.json").read_text(encoding="utf-8"))}
    return base


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="de")
    args = ap.parse_args()
    locale = _load_locale(args.lang)
    _PROD.mkdir(parents=True, exist_ok=True)
    _DEV.mkdir(parents=True, exist_ok=True)
    for tpl_path in sorted(_TEMPLATES.glob("*.json")):
        tpl = json.loads(tpl_path.read_text(encoding="utf-8"))
        rendered = render_dashboard(tpl, locale)
        rendered["time"] = {"from": "now-24h", "to": "now"}
        (_PROD / tpl_path.name).write_text(
            json.dumps(rendered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        dev = render_dashboard(tpl, locale)
        dev["time"] = {"from": "now-7d", "to": "now"}
        (_DEV / tpl_path.name).write_text(
            json.dumps(dev, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"built {len(list(_TEMPLATES.glob('*.json')))} dashboards for lang={args.lang}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd loginlogbook-api && uv run pytest tests/test_build_dashboards.py -v`
Expected: PASS (2 passed).

- [ ] **Step 7: Generate the German dashboards and confirm no drift**

Run: `cd loginlogbook-api && uv run python -m scripts.build_dashboards --lang de`
Then: `git diff --stat grafana/dashboards`
Expected: the regenerated German dashboards match the committed ones except for formatting; visually confirm titles are unchanged. Commit any intended formatting normalisation.

- [ ] **Step 8: Commit**

```bash
git add loginlogbook-api/app/locales/grafana loginlogbook-api/scripts/build_dashboards.py loginlogbook-api/grafana/templates loginlogbook-api/grafana/dashboards loginlogbook-api/grafana/dashboards-dev loginlogbook-api/tests/test_build_dashboards.py
git commit -m "feat(grafana): generate dashboards from templates and locale files"
```

---

## Task 9: Locale key-parity tests (all components)

**Files:**
- Create: `loginlogbook-api/tests/test_locale_parity.py`
- Create: `loginlogbook-client/tests/test_locale_parity.py`

**Interfaces:**
- Consumes: all locale directories created in Tasks 2, 3, 5, 8.

- [ ] **Step 1: Write the API parity test**

Create `loginlogbook-api/tests/test_locale_parity.py`:

```python
import json
from pathlib import Path

import pytest

_APP = Path(__file__).parent.parent / "app"
_DIRS = [_APP / "locales" / "api",
         _APP / "locales" / "admin",
         _APP / "locales" / "grafana"]


@pytest.mark.parametrize("locale_dir", _DIRS, ids=lambda p: p.name)
def test_every_language_has_same_keys_as_de(locale_dir: Path):
    de = set(json.loads((locale_dir / "de.json").read_text(encoding="utf-8")))
    for other in locale_dir.glob("*.json"):
        if other.name == "de.json":
            continue
        keys = set(json.loads(other.read_text(encoding="utf-8")))
        assert keys == de, f"{other} differs from de.json: " \
                           f"missing={de - keys}, extra={keys - de}"
```

- [ ] **Step 2: Run it**

Run: `cd loginlogbook-api && uv run pytest tests/test_locale_parity.py -v`
Expected: PASS (3 parametrized cases). If it fails, fix the offending `en.json` to match `de.json` keys exactly.

- [ ] **Step 3: Write the client parity test**

Create `loginlogbook-client/tests/test_locale_parity.py`:

```python
import json
from pathlib import Path

_LOCALES = Path(__file__).parent.parent / "app" / "locales"


def test_en_matches_de_keys():
    de = set(json.loads((_LOCALES / "de.json").read_text(encoding="utf-8")))
    en = set(json.loads((_LOCALES / "en.json").read_text(encoding="utf-8")))
    assert en == de, f"missing={de - en}, extra={en - de}"
```

- [ ] **Step 4: Run it**

Run: `cd loginlogbook-client && uv run pytest tests/test_locale_parity.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-api/tests/test_locale_parity.py loginlogbook-client/tests/test_locale_parity.py
git commit -m "test: enforce locale key parity across languages"
```

---

## Task 10: Full suite + docs note

**Files:**
- Modify: `CLAUDE.md` (project root) — short note on adding a language.

- [ ] **Step 1: Run both full suites**

Run: `cd loginlogbook-api && uv run pytest -q` — expected: all pass.
Run: `cd loginlogbook-client && uv run pytest -q` — expected: all pass.

- [ ] **Step 2: Add a short how-to note**

Append to `CLAUDE.md` a section:

```markdown
## Sprachen (i18n)

Feste UI-Texte liegen in JSON-Locale-Dateien. Aktive Sprache = serverseitig (`/data/settings.json`), umschaltbar in der Admin-UI. Neue Sprache `xx`:
1. `xx.json` je Verzeichnis aus `de.json` kopieren und übersetzen: `loginlogbook-client/app/locales/`, `loginlogbook-api/app/locales/{admin,api,grafana}/`.
2. Client/Admin/API: fertig (`xx` erscheint im Admin-Umschalter).
3. Grafana: `uv run python -m scripts.build_dashboards --lang xx` + `docker compose restart grafana`.
Key-Parität wird per Test erzwungen (`test_locale_parity.py`).
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document adding a language"
```

---

## Self-Review

**Spec coverage:**
- ✅ Einheitliches JSON-Format + Fallback-Kette → Tasks 2, 5 (`Translator`).
- ✅ Locale-Verzeichnisse je Komponente → Tasks 2, 3, 5, 8.
- ✅ `settings.json` + `SettingsStore` → Task 1.
- ✅ `GET /settings` (no auth) / `PUT /settings` (admin, 400 on bad code) → Task 3.
- ✅ `available` aus vorhandenen Dateien → Task 2 (`available()`), Task 3 (route).
- ✅ Locale-Static-Endpoint mit Regex-Validierung → Task 3.
- ✅ Client `Translator`, Sprachbezug via API, `language_changed`, Offline → Tasks 5, 6, 7.
- ✅ Admin-UI `data-i18n`, JS `t()`, Dropdown, `PUT` → Task 4.
- ✅ API-Texte → Task 2.
- ✅ Grafana Generator + Templates → Task 8.
- ✅ Erweiterbarkeit (neue Sprache = Datei) → Task 10 doc + parity test Task 9.
- ✅ Tests: translator, available, settings routes, locale endpoint, parity, generator → Tasks 2,3,8,9.
- ✅ Sicherheit: no-auth GET, admin PUT (403), regex code validation → Tasks 1,3.

**Notes for the implementer:**
- Offline client language: the spec asks the last language code be cached. Minimal approach — the client already caches recent data; persisting the last `settings.language` alongside that cache is optional polish. If the existing cache layer (`app/cache.py`) has an obvious slot, store it there; otherwise defaulting to `de` on a failed `/settings` fetch satisfies "nie leere UI" and is acceptable. Do not build a new cache subsystem for this.
- When editing `overlay_window.py` and `api_client.py`, match the real attribute names in those files (session, base URL, timeout, existing signals) rather than the illustrative names above.
- Run `build_dashboards.py --lang de` once and commit the normalised dashboards so future diffs are clean.
