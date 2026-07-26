# GNOME/Wayland Desktop-Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GNOME 50 Shell extension (`loginlogbook-gnome-extension/`) that enforces the LoginLogBook login-reason prompt under Wayland with a real `pushModal` input grab and full UI parity with the PyQt overlay.

**Architecture:** Standalone GJS/ESM extension. UI-free logic modules (`config`, `models`, `store`, `net`, `i18n`, pure UI helpers) are unit-tested headless with a minimal pure-gjs assert runner; the `St`/`Shell` integration (grab, widgets, orchestration) is verified via a documented manual smoke checklist. The extension talks to the existing `loginlogbook-api` over the same HTTP contract as the PyQt client, reuses `/etc/loginlogbook.env` and the shared cache/queue paths, and fails open on any config/startup error.

**Tech Stack:** GNOME Shell 50.1, gjs 1.88 (ESM), `gi://` typelibs (`GObject`, `Gio`, `GLib`, `Soup` 3.0, `St`, `Clutter`, `Shell`, `Meta`, `Gtk`? no), dconf system DB for enforced install. No npm/external runtime deps.

## Global Constraints

- GNOME Shell 50 / gjs 1.88; ESM extension; `metadata.json` `shell-version: ["50"]`, `uuid: "loginlogbook@ozon08.github.io"`.
- Only GJS + `gi://` typelibs (`GObject`, `Gio`, `GLib`, `Soup` 3.0, `St`, `Clutter`, `Shell`, `Meta`); **no npm/external runtime deps**.
- **Fail-open:** any config error / missing `API_URL` / unexpected `enable()` exception → no grab, log to journal, user gets in normally.
- Shared env/cache/queue with the PyQt client: read `/etc/loginlogbook.env`; same vars `API_URL`, `CLIENT_TOKEN`, `API_CA_BUNDLE`, `CACHE_DIR`, `QUEUE_FILE`; same defaults `~/.loginlogbook/cache`, `~/.loginlogbook/queue.json`.
- HTTP contract identical to the PyQt client: endpoints, header `X-Client-Token`, 5 s timeout.
- Submit payload: `EventIn { event_type:"login", host, os_user, reason: <selected label | free text>, timestamp: <ISO-8601> }`.
- UI texts from locale JSON only (no hardcoded strings); locale key parity with `de.json` enforced by test.
- Runs only in `user` session mode (not on the lock screen).
- Tests run headless via `gjs -m tests/run.js` from the extension directory.

---

## File Structure

```
loginlogbook-gnome-extension/
  metadata.json
  extension.js                 # default class extends Extension; enable()/disable()
  src/
    config.js                  # parseEnv(text) + loadConfig(path) + isUsable(cfg)
    models.js                  # Reason/EventIn/EventOut/AppConfig/BrandingConfig/LanguageSetting + safeLogoBg
    store.js                   # CacheStore + EventQueue
    net.js                     # ApiClient (injectable transport; default Soup 3)
    i18n.js                    # Translator (active -> de -> key)
    enforcement.js             # ModalGuard + monitorCovers() helper
    ui/
      helpers.js               # filterReasons/withinDays/reasonFromFreeText (pure)
      logo.js reasonList.js recentTable.js footer.js confirmDialog.js overlay.js
  locales/ de.json en.json
  tests/
    harness.js                 # minimal assert runner
    run.js                     # imports all *.test.js then reports
    config.test.js models.test.js store.test.js net.test.js i18n.test.js
    enforcement.test.js helpers.test.js metadata.test.js locale_parity.test.js
  packaging/ install.sh uninstall.sh
  README.md
```

---

## Task 1: Extension skeleton, metadata, and test harness

**Files:**
- Create: `loginlogbook-gnome-extension/metadata.json`
- Create: `loginlogbook-gnome-extension/extension.js`
- Create: `loginlogbook-gnome-extension/tests/harness.js`
- Create: `loginlogbook-gnome-extension/tests/run.js`
- Create: `loginlogbook-gnome-extension/tests/metadata.test.js`

**Interfaces:**
- Produces: `harness.js` exports `test(name, fn)`, `assertEqual(actual, expected, msg)`, `assertThrows(fn, msg)`, `report()` (returns exit code, prints summary). `run.js` is the CI entry (`gjs -m tests/run.js`). `metadata.json` has `uuid`, `name`, `description`, `shell-version:["50"]`, `url`.

- [ ] **Step 1: Write the failing test**

Create `tests/harness.js`:
```javascript
// Minimal pure-gjs assert runner. No external deps.
const _results = [];
export function test(name, fn) {
    try { fn(); _results.push([true, name, '']); }
    catch (e) { _results.push([false, name, String(e && e.message || e)]); }
}
export function assertEqual(actual, expected, msg = '') {
    const a = JSON.stringify(actual), b = JSON.stringify(expected);
    if (a !== b) throw new Error(`${msg}: ${a} !== ${b}`);
}
export function assertThrows(fn, msg = '') {
    let threw = false;
    try { fn(); } catch { threw = true; }
    if (!threw) throw new Error(`${msg}: expected throw`);
}
export function report() {
    let failed = 0;
    for (const [ok, name, err] of _results) {
        print(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok ? '' : ' — ' + err}`);
        if (!ok) failed++;
    }
    print(`\n${_results.length - failed}/${_results.length} passed`);
    return failed === 0 ? 0 : 1;
}
```

Create `tests/metadata.test.js`:
```javascript
import GLib from 'gi://GLib';
import { test, assertEqual } from './harness.js';

function readJson(rel) {
    const dir = GLib.path_get_dirname(GLib.path_get_dirname(import.meta.url.replace('file://', '')));
    const [ok, bytes] = GLib.file_get_contents(GLib.build_filenamev([dir, rel]));
    void ok;
    return JSON.parse(new TextDecoder().decode(bytes));
}

test('metadata has correct uuid', () => {
    assertEqual(readJson('metadata.json').uuid, 'loginlogbook@ozon08.github.io', 'uuid');
});
test('metadata targets shell 50', () => {
    assertEqual(readJson('metadata.json')['shell-version'], ['50'], 'shell-version');
});
```

Create `tests/run.js`:
```javascript
import system from 'system';
import { report } from './harness.js';
import './metadata.test.js';
system.exit(report());
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: FAIL — `metadata.json` cannot be read (file not found) or JSON parse error.

- [ ] **Step 3: Write minimal implementation**

Create `metadata.json`:
```json
{
    "uuid": "loginlogbook@ozon08.github.io",
    "name": "LoginLogBook",
    "description": "Enforces a login-reason prompt at GNOME/Wayland session start.",
    "shell-version": ["50"],
    "url": "https://github.com/OZON08/LoginLogBook"
}
```

Create `extension.js` (grab wiring comes in Task 9; for now a fail-open stub):
```javascript
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

export default class LoginLogBookExtension extends Extension {
    enable() {
        // Full orchestration is wired in Task 9. Fail-open by construction:
        // any error here must never leave the user locked out.
        try {
            log('[loginlogbook] enable(): skeleton — no guard yet');
        } catch (e) {
            logError(e, '[loginlogbook] enable failed — failing open');
        }
    }

    disable() {
        log('[loginlogbook] disable()');
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — `2/2 passed`.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/metadata.json loginlogbook-gnome-extension/extension.js loginlogbook-gnome-extension/tests/
git commit -m "feat(gnome-ext): skeleton, metadata, gjs test harness"
```

---

## Task 2: `config.js` — env parser and loader

**Files:**
- Create: `loginlogbook-gnome-extension/src/config.js`
- Create: `loginlogbook-gnome-extension/tests/config.test.js`
- Modify: `loginlogbook-gnome-extension/tests/run.js` (add import)

**Interfaces:**
- Produces:
  - `parseEnv(text)` → object of only the present `KEY: value` pairs (strips `#` comments, surrounding single/double quotes, whitespace).
  - `loadConfig(path, home)` → `{ apiUrl, clientToken, caBundle, cacheDir, queueFile }`. `caBundle` is `null` when unset. `home` defaults to `GLib.get_home_dir()`. Defaults: `cacheDir = ${home}/.loginlogbook/cache`, `queueFile = ${home}/.loginlogbook/queue.json`. Missing file → all defaults, `apiUrl=''`.
  - `isUsable(cfg)` → `cfg.apiUrl` is a non-empty string.

- [ ] **Step 1: Write the failing test**

Create `tests/config.test.js`:
```javascript
import { test, assertEqual } from './harness.js';
import { parseEnv, loadConfig, isUsable } from '../src/config.js';

test('parseEnv strips comments, quotes, whitespace', () => {
    const out = parseEnv([
        '# comment',
        'API_URL=https://llb.example.com',
        'CLIENT_TOKEN="secret token"',
        "REASONS_FILE='/x/y'",
        '',
        '  IGNORED_NO_EQUALS  ',
    ].join('\n'));
    assertEqual(out.API_URL, 'https://llb.example.com', 'API_URL');
    assertEqual(out.CLIENT_TOKEN, 'secret token', 'CLIENT_TOKEN');
    assertEqual(out.REASONS_FILE, '/x/y', 'quoted single');
    assertEqual('IGNORED_NO_EQUALS' in out, false, 'no-equals ignored');
});

test('loadConfig applies defaults when file missing', () => {
    const cfg = loadConfig('/nonexistent/loginlogbook.env', '/home/u');
    assertEqual(cfg.apiUrl, '', 'apiUrl empty');
    assertEqual(cfg.caBundle, null, 'caBundle null');
    assertEqual(cfg.cacheDir, '/home/u/.loginlogbook/cache', 'cacheDir default');
    assertEqual(cfg.queueFile, '/home/u/.loginlogbook/queue.json', 'queueFile default');
    assertEqual(isUsable(cfg), false, 'unusable without apiUrl');
});
```

Add to `tests/run.js` after the metadata import:
```javascript
import './config.test.js';
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: FAIL — `../src/config.js` import error (module not found).

- [ ] **Step 3: Write minimal implementation**

Create `src/config.js`:
```javascript
import GLib from 'gi://GLib';

export function parseEnv(text) {
    const out = {};
    for (let line of text.split('\n')) {
        line = line.trim();
        if (!line || line.startsWith('#')) continue;
        const eq = line.indexOf('=');
        if (eq === -1) continue;
        const key = line.slice(0, eq).trim();
        let val = line.slice(eq + 1).trim();
        if ((val.startsWith('"') && val.endsWith('"')) ||
            (val.startsWith("'") && val.endsWith("'")))
            val = val.slice(1, -1);
        out[key] = val;
    }
    return out;
}

export function loadConfig(path = '/etc/loginlogbook.env', home = GLib.get_home_dir()) {
    let env = {};
    try {
        const [ok, bytes] = GLib.file_get_contents(path);
        if (ok) env = parseEnv(new TextDecoder().decode(bytes));
    } catch {
        // fail-open: missing/unreadable env yields defaults
    }
    return {
        apiUrl: (env.API_URL || '').replace(/\/+$/, ''),
        clientToken: env.CLIENT_TOKEN || '',
        caBundle: env.API_CA_BUNDLE || null,
        cacheDir: env.CACHE_DIR || GLib.build_filenamev([home, '.loginlogbook', 'cache']),
        queueFile: env.QUEUE_FILE || GLib.build_filenamev([home, '.loginlogbook', 'queue.json']),
    };
}

export function isUsable(cfg) {
    return typeof cfg.apiUrl === 'string' && cfg.apiUrl.length > 0;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — config tests green.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/src/config.js loginlogbook-gnome-extension/tests/config.test.js loginlogbook-gnome-extension/tests/run.js
git commit -m "feat(gnome-ext): env config parser/loader with fail-open defaults"
```

---

## Task 3: `models.js` — data models mirroring the API contract

**Files:**
- Create: `loginlogbook-gnome-extension/src/models.js`
- Create: `loginlogbook-gnome-extension/tests/models.test.js`
- Modify: `loginlogbook-gnome-extension/tests/run.js` (add import)

**Interfaces:**
- Produces:
  - `Reason(o)` → `{ id, label, active }` (`active` defaults `true`).
  - `AppConfig(o)` → `{ recent_days=7, allow_free_text=true }`.
  - `BrandingConfig(o)` → `{ logo_height=120, logo_bg='#1E293B' }`.
  - `LanguageSetting(o)` → `{ language='de', available=[] }`.
  - `EventIn(o)` → `{ event_type, host, os_user, reason, timestamp }`; throws if `event_type ∉ {login,logout}` or `host`/`os_user`/`timestamp` missing; `reason` defaults `null`. This object is the exact POST body.
  - `EventOut(o)` → same shape as `EventIn`, no throw (tolerant read model).
  - `safeLogoBg(hex)` → `hex` if it matches `^#[0-9A-Fa-f]{6}$`, else `'#1E293B'`.

- [ ] **Step 1: Write the failing test**

Create `tests/models.test.js`:
```javascript
import { test, assertEqual, assertThrows } from './harness.js';
import { Reason, EventIn, AppConfig, BrandingConfig, LanguageSetting, safeLogoBg } from '../src/models.js';

test('Reason defaults active=true', () => {
    assertEqual(Reason({ id: 'a', label: 'A' }), { id: 'a', label: 'A', active: true }, 'reason');
});
test('EventIn builds wire body and defaults reason=null', () => {
    const e = EventIn({ event_type: 'login', host: 'h', os_user: 'u', timestamp: '2026-07-20T10:00:00' });
    assertEqual(e, { event_type: 'login', host: 'h', os_user: 'u', reason: null, timestamp: '2026-07-20T10:00:00' }, 'eventin');
});
test('EventIn rejects bad event_type', () => {
    assertThrows(() => EventIn({ event_type: 'nope', host: 'h', os_user: 'u', timestamp: 't' }), 'bad type');
});
test('EventIn rejects missing host', () => {
    assertThrows(() => EventIn({ event_type: 'login', os_user: 'u', timestamp: 't' }), 'missing host');
});
test('defaults for config models', () => {
    assertEqual(AppConfig({}), { recent_days: 7, allow_free_text: true }, 'appconfig');
    assertEqual(BrandingConfig({}), { logo_height: 120, logo_bg: '#1E293B' }, 'branding');
    assertEqual(LanguageSetting({}), { language: 'de', available: [] }, 'language');
});
test('safeLogoBg validates hex', () => {
    assertEqual(safeLogoBg('#AbC123'), '#AbC123', 'valid');
    assertEqual(safeLogoBg('red'), '#1E293B', 'invalid');
});
```

Add to `tests/run.js`:
```javascript
import './models.test.js';
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: FAIL — `../src/models.js` not found.

- [ ] **Step 3: Write minimal implementation**

Create `src/models.js`:
```javascript
const HEX = /^#[0-9A-Fa-f]{6}$/;

export function safeLogoBg(hex) {
    return typeof hex === 'string' && HEX.test(hex) ? hex : '#1E293B';
}

export function Reason(o = {}) {
    return { id: o.id, label: o.label, active: o.active === undefined ? true : !!o.active };
}

export function AppConfig(o = {}) {
    return {
        recent_days: o.recent_days === undefined ? 7 : o.recent_days,
        allow_free_text: o.allow_free_text === undefined ? true : !!o.allow_free_text,
    };
}

export function BrandingConfig(o = {}) {
    return {
        logo_height: o.logo_height === undefined ? 120 : o.logo_height,
        logo_bg: o.logo_bg === undefined ? '#1E293B' : o.logo_bg,
    };
}

export function LanguageSetting(o = {}) {
    return { language: o.language || 'de', available: o.available || [] };
}

export function EventIn(o = {}) {
    if (o.event_type !== 'login' && o.event_type !== 'logout')
        throw new Error(`invalid event_type: ${o.event_type}`);
    for (const k of ['host', 'os_user', 'timestamp'])
        if (!o[k]) throw new Error(`missing ${k}`);
    return {
        event_type: o.event_type,
        host: o.host,
        os_user: o.os_user,
        reason: o.reason === undefined ? null : o.reason,
        timestamp: o.timestamp,
    };
}

export function EventOut(o = {}) {
    return {
        event_type: o.event_type,
        host: o.host,
        os_user: o.os_user,
        reason: o.reason === undefined ? null : o.reason,
        timestamp: o.timestamp,
    };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — model tests green.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/src/models.js loginlogbook-gnome-extension/tests/models.test.js loginlogbook-gnome-extension/tests/run.js
git commit -m "feat(gnome-ext): data models mirroring the API contract"
```

---

## Task 4: `store.js` — cache and offline queue

**Files:**
- Create: `loginlogbook-gnome-extension/src/store.js`
- Create: `loginlogbook-gnome-extension/tests/store.test.js`
- Modify: `loginlogbook-gnome-extension/tests/run.js` (add import)

**Interfaces:**
- Consumes: `Reason`, `EventOut`, `AppConfig` from `models.js`.
- Produces:
  - `class CacheStore { constructor(dir) }` with `saveReasons(list)/loadReasons()`, `saveLogo(bytes, contentType)/loadLogo()→{data,contentType}|null`, `saveRecent(list)/loadRecent()`, `saveConfig(cfg)/loadConfig()`. Missing file → `null`. Creates `dir` on construction.
  - `class EventQueue { constructor(path) }` with `enqueue(evt)`, `flush(postFn)→count` (posts each via `postFn(evt)`, keeps failures — `postFn` throwing/returning rejected means keep), `pendingCount()→number`. Creates parent dir on construction.
  - `flush` is synchronous over an async `postFn`: it awaits each. Signature `async flush(postFn)`.

- [ ] **Step 1: Write the failing test**

Create `tests/store.test.js`:
```javascript
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import { test, assertEqual } from './harness.js';
import { CacheStore, EventQueue } from '../src/store.js';

function tmpdir() {
    const d = GLib.build_filenamev([GLib.get_tmp_dir(), 'llb-' + Math.random().toString(36).slice(2)]);
    Gio.File.new_for_path(d).make_directory_with_parents(null);
    return d;
}

test('CacheStore round-trips reasons and returns null when absent', () => {
    const c = new CacheStore(tmpdir());
    assertEqual(c.loadReasons(), null, 'absent');
    c.saveReasons([{ id: 'a', label: 'A', active: true }]);
    assertEqual(c.loadReasons(), [{ id: 'a', label: 'A', active: true }], 'roundtrip');
});

test('EventQueue enqueue/flush keeps failures', async () => {
    const q = new EventQueue(GLib.build_filenamev([tmpdir(), 'queue.json']));
    q.enqueue({ event_type: 'login', host: 'h', os_user: 'u', reason: 'r', timestamp: 't' });
    q.enqueue({ event_type: 'login', host: 'h', os_user: 'u', reason: 's', timestamp: 't' });
    assertEqual(q.pendingCount(), 2, 'two pending');
    let calls = 0;
    const sent = await q.flush(async (e) => { calls++; if (e.reason === 's') throw new Error('fail'); });
    assertEqual(sent, 1, 'one sent');
    assertEqual(q.pendingCount(), 1, 'one kept');
});
```

Add to `tests/run.js`:
```javascript
import './store.test.js';
```

Note: `run.js` must `await` async tests. Update the harness call site — see Step 3 harness note.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: FAIL — `../src/store.js` not found.

- [ ] **Step 3: Write minimal implementation**

First make the harness async-aware. Edit `tests/harness.js` — replace `test` and add `runAll`:
```javascript
const _results = [];
const _pending = [];
export function test(name, fn) {
    _pending.push([name, fn]);
}
export async function runAll() {
    for (const [name, fn] of _pending) {
        try { await fn(); _results.push([true, name, '']); }
        catch (e) { _results.push([false, name, String(e && e.message || e)]); }
    }
}
```
Edit `tests/run.js` to await:
```javascript
import system from 'system';
import { report, runAll } from './harness.js';
import './metadata.test.js';
import './config.test.js';
import './models.test.js';
import './store.test.js';
await runAll();
system.exit(report());
```

Create `src/store.js`:
```javascript
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

function readText(path) {
    const f = Gio.File.new_for_path(path);
    if (!f.query_exists(null)) return null;
    const [ok, bytes] = f.load_contents(null);
    if (!ok) return null;
    return new TextDecoder().decode(bytes);
}
function writeText(path, text) {
    Gio.File.new_for_path(path).replace_contents(
        new TextEncoder().encode(text), null, false,
        Gio.FileCreateFlags.REPLACE_DESTINATION, null);
}
function ensureDir(path) {
    const f = Gio.File.new_for_path(path);
    if (!f.query_exists(null)) f.make_directory_with_parents(null);
}

export class CacheStore {
    constructor(dir) { this._dir = dir; ensureDir(dir); }
    _p(name) { return GLib.build_filenamev([this._dir, name]); }

    saveReasons(list) { writeText(this._p('reasons.json'), JSON.stringify(list)); }
    loadReasons() { const t = readText(this._p('reasons.json')); return t ? JSON.parse(t) : null; }

    saveLogo(bytes, contentType) {
        Gio.File.new_for_path(this._p('logo.bin')).replace_contents(
            bytes, null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        writeText(this._p('logo_meta.json'), JSON.stringify({ content_type: contentType }));
    }
    loadLogo() {
        const bin = Gio.File.new_for_path(this._p('logo.bin'));
        const meta = readText(this._p('logo_meta.json'));
        if (!bin.query_exists(null) || !meta) return null;
        const [ok, bytes] = bin.load_contents(null);
        if (!ok) return null;
        return { data: bytes, contentType: JSON.parse(meta).content_type };
    }

    saveRecent(list) { writeText(this._p('recent_events.json'), JSON.stringify(list)); }
    loadRecent() { const t = readText(this._p('recent_events.json')); return t ? JSON.parse(t) : null; }

    saveConfig(cfg) { writeText(this._p('config.json'), JSON.stringify(cfg)); }
    loadConfig() { const t = readText(this._p('config.json')); return t ? JSON.parse(t) : null; }
}

export class EventQueue {
    constructor(path) { this._path = path; ensureDir(GLib.path_get_dirname(path)); }
    _load() { const t = readText(this._path); return t ? JSON.parse(t) : []; }
    _save(list) { writeText(this._path, JSON.stringify(list)); }
    enqueue(evt) { const l = this._load(); l.push(evt); this._save(l); }
    pendingCount() { return this._load().length; }
    async flush(postFn) {
        const events = this._load();
        if (!events.length) return 0;
        const remaining = []; let sent = 0;
        for (const raw of events) {
            try { await postFn(raw); sent++; }
            catch { remaining.push(raw); }
        }
        this._save(remaining);
        return sent;
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — store tests green, all prior tests still green.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/src/store.js loginlogbook-gnome-extension/tests/store.test.js loginlogbook-gnome-extension/tests/harness.js loginlogbook-gnome-extension/tests/run.js
git commit -m "feat(gnome-ext): file-backed cache and offline event queue"
```

---

## Task 5: `net.js` — API client with injectable transport

**Files:**
- Create: `loginlogbook-gnome-extension/src/net.js`
- Create: `loginlogbook-gnome-extension/tests/net.test.js`
- Modify: `loginlogbook-gnome-extension/tests/run.js` (add import)

**Interfaces:**
- Consumes: `Reason`, `EventOut`, `AppConfig`, `BrandingConfig`, `LanguageSetting`, `EventIn` from `models.js`.
- Produces: `class ApiClient { constructor({ apiUrl, clientToken, caBundle, transport }) }`. `transport` is optional; default builds a Soup 3 transport. A transport is `async ({method, url, headers, body}) → { status, bytes, headers }` where `bytes` is a `Uint8Array` and `headers` is a plain object with lowercased keys. Methods (all async):
  - `getReasons() → Reason[]`
  - `getLogo() → { data: Uint8Array, contentType: string }`
  - `getConfig() → AppConfig`
  - `getBrandingConfig() → BrandingConfig`
  - `getSettings() → LanguageSetting`
  - `getRecentEvents(host, days) → EventOut[]`
  - `postEvent(evt) → void` (throws on non-2xx)
- Every request sends header `X-Client-Token: <clientToken>`. Non-2xx status throws.

- [ ] **Step 1: Write the failing test**

Create `tests/net.test.js`:
```javascript
import { test, assertEqual } from './harness.js';
import { ApiClient } from '../src/net.js';

function recorder(responses) {
    const calls = [];
    const transport = async ({ method, url, headers, body }) => {
        calls.push({ method, url, headers, body });
        const r = responses.shift();
        return { status: r.status, bytes: new TextEncoder().encode(r.text || ''), headers: r.headers || {} };
    };
    return { transport, calls };
}

test('getReasons sends token header and parses list', async () => {
    const { transport, calls } = recorder([{ status: 200, text: JSON.stringify([{ id: 'a', label: 'A' }]) }]);
    const api = new ApiClient({ apiUrl: 'https://x', clientToken: 'T', transport });
    const reasons = await api.getReasons();
    assertEqual(reasons, [{ id: 'a', label: 'A', active: true }], 'parsed');
    assertEqual(calls[0].url, 'https://x/reasons', 'url');
    assertEqual(calls[0].headers['X-Client-Token'], 'T', 'header');
});

test('getRecentEvents builds query string', async () => {
    const { transport, calls } = recorder([{ status: 200, text: '[]' }]);
    const api = new ApiClient({ apiUrl: 'https://x', clientToken: 'T', transport });
    await api.getRecentEvents('host1', 7);
    assertEqual(calls[0].url, 'https://x/events/recent?host=host1&days=7&limit=100', 'query');
});

test('postEvent throws on non-2xx', async () => {
    const { transport } = recorder([{ status: 503, text: 'down' }]);
    const api = new ApiClient({ apiUrl: 'https://x', clientToken: 'T', transport });
    let threw = false;
    try { await api.postEvent({ event_type: 'login', host: 'h', os_user: 'u', reason: 'r', timestamp: 't' }); }
    catch { threw = true; }
    assertEqual(threw, true, 'threw');
});
```

Add to `tests/run.js`:
```javascript
import './net.test.js';
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: FAIL — `../src/net.js` not found.

- [ ] **Step 3: Write minimal implementation**

Create `src/net.js`:
```javascript
import { Reason, EventOut, AppConfig, BrandingConfig, LanguageSetting } from './models.js';

const TIMEOUT = 5;

function soupTransport({ caBundle }) {
    // Imported lazily so unit tests never need Soup.
    const Soup = imports.gi.Soup;
    const Gio = imports.gi.Gio;
    const session = new Soup.Session();
    session.timeout = TIMEOUT;
    if (caBundle) {
        try { session.tls_database = Gio.TlsFileDatabase.new(caBundle); } catch (e) { logError(e); }
    }
    return async ({ method, url, headers, body }) => {
        const msg = Soup.Message.new(method, url);
        for (const [k, v] of Object.entries(headers || {}))
            msg.request_headers.append(k, v);
        if (body !== undefined && body !== null) {
            const bytes = new TextEncoder().encode(body);
            msg.set_request_body_from_bytes('application/json', new GLib.Bytes(bytes));
        }
        const gbytes = await new Promise((resolve, reject) => {
            session.send_and_read_async(msg, 0, null, (s, res) => {
                try { resolve(s.send_and_read_finish(res)); } catch (e) { reject(e); }
            });
        });
        const outHeaders = {};
        msg.response_headers.foreach((name, value) => { outHeaders[name.toLowerCase()] = value; });
        const arr = gbytes ? new Uint8Array(gbytes.get_data() || []) : new Uint8Array();
        return { status: msg.get_status(), bytes: arr, headers: outHeaders };
    };
}

// GLib needed only inside soupTransport; import here to keep it out of unit path.
import GLib from 'gi://GLib';

export class ApiClient {
    constructor({ apiUrl, clientToken, caBundle = null, transport = null }) {
        this._base = (apiUrl || '').replace(/\/+$/, '');
        this._headers = { 'X-Client-Token': clientToken || '' };
        this._transport = transport || soupTransport({ caBundle });
    }

    async _get(path, query) {
        let url = `${this._base}${path}`;
        if (query) {
            const qs = Object.entries(query).map(([k, v]) => `${k}=${v}`).join('&');
            url += `?${qs}`;
        }
        const r = await this._transport({ method: 'GET', url, headers: this._headers });
        if (r.status < 200 || r.status >= 300) throw new Error(`GET ${path} -> ${r.status}`);
        return r;
    }

    _json(r) { return JSON.parse(new TextDecoder().decode(r.bytes)); }

    async getReasons() { return this._json(await this._get('/reasons')).map(Reason); }
    async getLogo() {
        const r = await this._get('/branding/logo');
        return { data: r.bytes, contentType: r.headers['content-type'] || 'image/png' };
    }
    async getConfig() { return AppConfig(this._json(await this._get('/config'))); }
    async getBrandingConfig() { return BrandingConfig(this._json(await this._get('/branding/config'))); }
    async getSettings() { return LanguageSetting(this._json(await this._get('/settings'))); }
    async getRecentEvents(host, days) {
        return this._json(await this._get('/events/recent', { host, days, limit: 100 })).map(EventOut);
    }
    async postEvent(evt) {
        const r = await this._transport({
            method: 'POST', url: `${this._base}/events`,
            headers: { ...this._headers, 'Content-Type': 'application/json' },
            body: JSON.stringify(evt),
        });
        if (r.status < 200 || r.status >= 300) throw new Error(`POST /events -> ${r.status}`);
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — net tests green (mock transport, Soup never loaded).

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/src/net.js loginlogbook-gnome-extension/tests/net.test.js loginlogbook-gnome-extension/tests/run.js
git commit -m "feat(gnome-ext): API client with injectable transport (Soup 3 default)"
```

---

## Task 6: `i18n.js` + bundled locales + parity test

**Files:**
- Create: `loginlogbook-gnome-extension/src/i18n.js`
- Create: `loginlogbook-gnome-extension/locales/de.json` (copy of client `de.json`)
- Create: `loginlogbook-gnome-extension/locales/en.json` (copy of client `en.json`)
- Create: `loginlogbook-gnome-extension/tests/i18n.test.js`
- Create: `loginlogbook-gnome-extension/tests/locale_parity.test.js`
- Modify: `loginlogbook-gnome-extension/tests/run.js` (add imports)

**Interfaces:**
- Produces: `class Translator { constructor(localesDir) }` with `setLanguage(code)`, `t(key, kwargs)` (fallback active → `de` → key; `{name}`-style interpolation from `kwargs`), `available()` (sorted locale stems).

- [ ] **Step 1: Write the failing test**

Copy the client locales first (they are the source of truth):
```bash
cp loginlogbook-client/app/locales/de.json loginlogbook-gnome-extension/locales/de.json
cp loginlogbook-client/app/locales/en.json loginlogbook-gnome-extension/locales/en.json
```

Create `tests/i18n.test.js`:
```javascript
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import { test, assertEqual } from './harness.js';
import { Translator } from '../src/i18n.js';

function fixtureDir() {
    const d = GLib.build_filenamev([GLib.get_tmp_dir(), 'llb-loc-' + Math.random().toString(36).slice(2)]);
    Gio.File.new_for_path(d).make_directory_with_parents(null);
    const write = (n, o) => Gio.File.new_for_path(GLib.build_filenamev([d, n]))
        .replace_contents(new TextEncoder().encode(JSON.stringify(o)), null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, null);
    write('de.json', { greet: 'Hallo {name}', only_de: 'DE' });
    write('en.json', { greet: 'Hello {name}' });
    return d;
}

test('t interpolates and falls back active -> de -> key', () => {
    const tr = new Translator(fixtureDir());
    tr.setLanguage('en');
    assertEqual(tr.t('greet', { name: 'X' }), 'Hello X', 'active');
    assertEqual(tr.t('only_de'), 'DE', 'fallback to de');
    assertEqual(tr.t('missing'), 'missing', 'fallback to key');
});
test('available lists sorted stems', () => {
    assertEqual(new Translator(fixtureDir()).available(), ['de', 'en'], 'available');
});
```

Create `tests/locale_parity.test.js`:
```javascript
import GLib from 'gi://GLib';
import { test, assertEqual } from './harness.js';

function localesDir() {
    const testsDir = GLib.path_get_dirname(import.meta.url.replace('file://', ''));
    return GLib.build_filenamev([GLib.path_get_dirname(testsDir), 'locales']);
}
function keys(name) {
    const [, bytes] = GLib.file_get_contents(GLib.build_filenamev([localesDir(), name]));
    return Object.keys(JSON.parse(new TextDecoder().decode(bytes))).sort();
}

test('en.json has the same keys as de.json', () => {
    assertEqual(keys('en.json'), keys('de.json'), 'parity en vs de');
});
```

Add to `tests/run.js`:
```javascript
import './i18n.test.js';
import './locale_parity.test.js';
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: FAIL — `../src/i18n.js` not found.

- [ ] **Step 3: Write minimal implementation**

Create `src/i18n.js`:
```javascript
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';

const DEFAULT = 'de';

export class Translator {
    constructor(localesDir) { this._dir = localesDir; this._cache = {}; this._active = DEFAULT; }
    _load(code) {
        if (!(code in this._cache)) {
            const path = GLib.build_filenamev([this._dir, `${code}.json`]);
            const f = Gio.File.new_for_path(path);
            if (f.query_exists(null)) {
                const [ok, bytes] = f.load_contents(null);
                this._cache[code] = ok ? JSON.parse(new TextDecoder().decode(bytes)) : {};
            } else {
                this._cache[code] = {};
            }
        }
        return this._cache[code];
    }
    setLanguage(code) { this._active = code || DEFAULT; }
    t(key, kwargs) {
        let text = this._load(this._active)[key];
        if (text === undefined) text = this._load(DEFAULT)[key];
        if (text === undefined) text = key;
        if (kwargs) for (const [k, v] of Object.entries(kwargs))
            text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
        return text;
    }
    available() {
        const dir = Gio.File.new_for_path(this._dir);
        const out = [];
        const en = dir.enumerate_children('standard::name', 0, null);
        let info;
        while ((info = en.next_file(null)) !== null) {
            const n = info.get_name();
            if (n.endsWith('.json')) out.push(n.slice(0, -5));
        }
        return out.sort();
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — i18n + parity green.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/src/i18n.js loginlogbook-gnome-extension/locales/ loginlogbook-gnome-extension/tests/i18n.test.js loginlogbook-gnome-extension/tests/locale_parity.test.js loginlogbook-gnome-extension/tests/run.js
git commit -m "feat(gnome-ext): translator, bundled locales, and parity test"
```

---

## Task 7: `enforcement.js` — ModalGuard + monitor geometry

**Files:**
- Create: `loginlogbook-gnome-extension/src/enforcement.js`
- Create: `loginlogbook-gnome-extension/tests/enforcement.test.js`
- Modify: `loginlogbook-gnome-extension/tests/run.js` (add import)

**Interfaces:**
- Produces:
  - `monitorCovers(monitors)` → array mapping each `{x,y,width,height}` monitor to a cover rect `{x,y,width,height}` (pure; identity geometry — one full-bleed rect per monitor). Unit-tested.
  - `class ModalGuard { constructor({ Main, actor }) }` with `engage() → bool` (calls `Main.pushModal(actor, { actionMode })`, sets `_active`, returns success), `release()` (idempotent; calls `Main.popModal(this._grab || actor)` once), `isActive() → bool`. `Main` and `actor` are injected so the state machine (idempotent release, engage/return) is unit-tested with a fake `Main`; the real grab is exercised in the manual smoke test (Task 9).

- [ ] **Step 1: Write the failing test**

Create `tests/enforcement.test.js`:
```javascript
import { test, assertEqual } from './harness.js';
import { monitorCovers, ModalGuard } from '../src/enforcement.js';

test('monitorCovers yields one full rect per monitor', () => {
    const covers = monitorCovers([{ x: 0, y: 0, width: 1920, height: 1080 }, { x: 1920, y: 0, width: 1280, height: 1024 }]);
    assertEqual(covers, [{ x: 0, y: 0, width: 1920, height: 1080 }, { x: 1920, y: 0, width: 1280, height: 1024 }], 'covers');
});

test('ModalGuard engage/release is idempotent', () => {
    let pushes = 0, pops = 0;
    const fakeMain = {
        pushModal: () => { pushes++; return { _grab: true }; },
        popModal: () => { pops++; },
    };
    const g = new ModalGuard({ Main: fakeMain, actor: {} });
    assertEqual(g.engage(), true, 'engaged');
    assertEqual(g.isActive(), true, 'active');
    g.release(); g.release();
    assertEqual(pushes, 1, 'one push');
    assertEqual(pops, 1, 'one pop despite double release');
    assertEqual(g.isActive(), false, 'inactive');
});
```

Add to `tests/run.js`:
```javascript
import './enforcement.test.js';
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: FAIL — `../src/enforcement.js` not found.

- [ ] **Step 3: Write minimal implementation**

Create `src/enforcement.js`:
```javascript
// Shell.ActionMode.SYSTEM_MODAL === 1 << 11 in GNOME Shell. Kept as a literal
// so this module never needs the Shell typelib at unit-test time.
const SYSTEM_MODAL = 1 << 11;

export function monitorCovers(monitors) {
    return monitors.map(m => ({ x: m.x, y: m.y, width: m.width, height: m.height }));
}

export class ModalGuard {
    constructor({ Main, actor }) {
        this._Main = Main;
        this._actor = actor;
        this._grab = null;
        this._active = false;
    }
    engage() {
        if (this._active) return true;
        this._grab = this._Main.pushModal(this._actor, { actionMode: SYSTEM_MODAL });
        this._active = !!this._grab;
        return this._active;
    }
    release() {
        if (!this._active) return;
        this._Main.popModal(this._grab || this._actor);
        this._grab = null;
        this._active = false;
    }
    isActive() { return this._active; }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — enforcement state machine + geometry green.

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/src/enforcement.js loginlogbook-gnome-extension/tests/enforcement.test.js loginlogbook-gnome-extension/tests/run.js
git commit -m "feat(gnome-ext): ModalGuard grab state machine + monitor geometry"
```

---

## Task 8: UI pure helpers + St widget modules

**Files:**
- Create: `loginlogbook-gnome-extension/src/ui/helpers.js`
- Create: `loginlogbook-gnome-extension/tests/helpers.test.js`
- Create: `loginlogbook-gnome-extension/src/ui/logo.js`
- Create: `loginlogbook-gnome-extension/src/ui/reasonList.js`
- Create: `loginlogbook-gnome-extension/src/ui/recentTable.js`
- Create: `loginlogbook-gnome-extension/src/ui/footer.js`
- Create: `loginlogbook-gnome-extension/src/ui/confirmDialog.js`
- Create: `loginlogbook-gnome-extension/src/ui/overlay.js`
- Modify: `loginlogbook-gnome-extension/tests/run.js` (add helpers import)

**Interfaces:**
- Consumes: `Translator` (`t`), `Reason`, `safeLogoBg`, `EventOut`.
- Produces (pure, tested — `ui/helpers.js`):
  - `filterReasons(reasons, query) → Reason[]` (case-insensitive substring on `label`; empty query → active reasons only, in original order).
  - `withinDays(events, days, nowMs) → EventOut[]` (keep events whose `timestamp` is within `days` of `nowMs`).
  - `reasonFromFreeText(text) → Reason|null` (`{ id:'', label: trimmed, active:true }`, or `null` when blank).
- Produces (St widgets — verified manually in Task 9):
  - `Overlay` (GObject class extending `St.Widget`) with `constructor(t, { onSubmit, onLogout })`, methods `setBranding(brandingCfg)`, `setLogo({data,contentType})`, `setReasons(list)`, `setRecent(events, days)`, `setStatus(online)`, `retranslate()`, `getCoverActors() → Clutter.Actor[]`, and a primary actor for the grab. `onSubmit(reasonLabel)` / `onLogout()` are callbacks.

- [ ] **Step 1: Write the failing test** (pure helpers only)

Create `tests/helpers.test.js`:
```javascript
import { test, assertEqual } from './harness.js';
import { filterReasons, withinDays, reasonFromFreeText } from '../src/ui/helpers.js';

const reasons = [
    { id: '1', label: 'Wartung', active: true },
    { id: '2', label: 'Update', active: true },
    { id: '3', label: 'Alt', active: false },
];

test('filterReasons: empty query returns active only', () => {
    assertEqual(filterReasons(reasons, ''), [reasons[0], reasons[1]], 'active only');
});
test('filterReasons: case-insensitive substring', () => {
    assertEqual(filterReasons(reasons, 'up'), [reasons[1]], 'match update');
});
test('withinDays keeps recent, drops old', () => {
    const now = Date.parse('2026-07-20T12:00:00Z');
    const evs = [
        { timestamp: '2026-07-19T12:00:00Z', host: 'h', os_user: 'u', event_type: 'login', reason: null },
        { timestamp: '2026-07-01T12:00:00Z', host: 'h', os_user: 'u', event_type: 'login', reason: null },
    ];
    assertEqual(withinDays(evs, 7, now).length, 1, 'one within 7 days');
});
test('reasonFromFreeText trims and rejects blank', () => {
    assertEqual(reasonFromFreeText('  Hallo '), { id: '', label: 'Hallo', active: true }, 'trim');
    assertEqual(reasonFromFreeText('   '), null, 'blank');
});
```

Add to `tests/run.js`:
```javascript
import './helpers.test.js';
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: FAIL — `../src/ui/helpers.js` not found.

- [ ] **Step 3: Write minimal implementation**

Create `src/ui/helpers.js`:
```javascript
export function filterReasons(reasons, query) {
    const q = (query || '').trim().toLowerCase();
    if (!q) return reasons.filter(r => r.active !== false);
    return reasons.filter(r => r.active !== false && r.label.toLowerCase().includes(q));
}
export function withinDays(events, days, nowMs) {
    const cutoff = nowMs - days * 86400000;
    return events.filter(e => Date.parse(e.timestamp) >= cutoff);
}
export function reasonFromFreeText(text) {
    const label = (text || '').trim();
    return label ? { id: '', label, active: true } : null;
}
```

Create the St widget modules. These are verified manually (Task 9) — no headless test. Create `src/ui/logo.js`:
```javascript
import GObject from 'gi://GObject';
import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import { safeLogoBg } from '../models.js';

export const Logo = GObject.registerClass(class Logo extends St.Bin {
    _init() {
        super._init({ style_class: 'llb-logo', x_align: St.Align.MIDDLE });
        this._img = new St.Icon({ icon_size: 96 });
        this.set_child(this._img);
    }
    setBranding(branding) {
        this.style = `background-color: ${safeLogoBg(branding.logo_bg)}; padding: 16px;`;
        this._img.icon_size = branding.logo_height || 120;
    }
    // Write bytes to a temp file and load as a file icon (avoids GdkPixbuf dep).
    setLogo({ data }) {
        const path = GLib.build_filenamev([GLib.get_tmp_dir(), 'llb-logo.bin']);
        Gio.File.new_for_path(path).replace_contents(
            data, null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        this._img.gicon = Gio.FileIcon.new(Gio.File.new_for_path(path));
    }
});
```

Create `src/ui/reasonList.js`:
```javascript
import GObject from 'gi://GObject';
import St from 'gi://St';
import { filterReasons } from './helpers.js';

export const ReasonList = GObject.registerClass({
    Signals: { 'selection-changed': { param_types: [GObject.TYPE_STRING] } },
}, class ReasonList extends St.BoxLayout {
    _init() {
        super._init({ vertical: true, style_class: 'llb-reasons' });
        this._all = [];
        this._selected = null;
    }
    populate(reasons) { this._all = reasons; this._render(''); }
    applyFilter(query) { this._render(query); }
    selectedLabel() { return this._selected; }
    _render(query) {
        this.destroy_all_children();
        for (const r of filterReasons(this._all, query)) {
            const btn = new St.Button({ label: r.label, style_class: 'llb-reason', x_expand: true });
            btn.connect('clicked', () => {
                this._selected = r.label;
                this.emit('selection-changed', r.label);
            });
            this.add_child(btn);
        }
    }
});
```

Create `src/ui/recentTable.js`:
```javascript
import GObject from 'gi://GObject';
import St from 'gi://St';
import { withinDays } from './helpers.js';

export const RecentTable = GObject.registerClass(class RecentTable extends St.BoxLayout {
    _init() { super._init({ vertical: true, style_class: 'llb-recent' }); }
    populate(events, days) {
        this.destroy_all_children();
        for (const e of withinDays(events || [], days, Date.now())) {
            const row = `${e.timestamp}  ${e.os_user}  ${e.event_type}  ${e.reason || ''}`;
            this.add_child(new St.Label({ text: row, style_class: 'llb-recent-row' }));
        }
    }
    retranslate() { /* rows are data, not localized */ }
});
```

Create `src/ui/footer.js`:
```javascript
import GObject from 'gi://GObject';
import St from 'gi://St';

export const Footer = GObject.registerClass(class Footer extends St.BoxLayout {
    _init(t, version) {
        super._init({ style_class: 'llb-footer' });
        this._t = t;
        this._userHost = new St.Label({ text: '' });
        this._status = new St.Label({ text: '' });
        this._version = new St.Label({ text: `v${version}` });
        this.add_child(this._userHost);
        this.add_child(this._status);
        this.add_child(this._version);
    }
    setUserHost(user, host) { this._userHost.text = `${user}@${host}`; }
    setStatus(online) { this._status.text = this._t(online ? 'client.status.online' : 'client.status.offline'); }
    retranslate() { /* status re-set by caller via setStatus */ }
});
```

Create `src/ui/confirmDialog.js`:
```javascript
import GObject from 'gi://GObject';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';

export const ConfirmDialog = GObject.registerClass(class ConfirmDialog extends ModalDialog.ModalDialog {
    _init(t, onConfirm) {
        super._init({ styleClass: 'llb-confirm' });
        this.contentLayout.add_child(new imports.gi.St.Label({ text: t('client.dialog.logout.confirm') }));
        this.setButtons([
            { label: t('client.button.cancel'), action: () => this.close(), key: imports.gi.Clutter.KEY_Escape },
            { label: t('client.button.logout.noreason'), action: () => { this.close(); onConfirm(); } },
        ]);
    }
});
```

Create `src/ui/overlay.js` (assembles the card; the primary actor is what the grab targets):
```javascript
import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Logo } from './logo.js';
import { ReasonList } from './reasonList.js';
import { RecentTable } from './recentTable.js';
import { Footer } from './footer.js';
import { reasonFromFreeText } from './helpers.js';

export const Overlay = GObject.registerClass(class Overlay extends St.Widget {
    _init(t, version, { onSubmit, onLogout }) {
        super._init({ style_class: 'llb-overlay', reactive: true,
            layout_manager: new Clutter.BinLayout() });
        this._t = t;
        this._onSubmit = onSubmit;
        this._covers = [];
        this._buildCovers();

        const card = new St.BoxLayout({ vertical: true, style_class: 'llb-card' });
        this._logo = new Logo();
        this._search = new St.Entry({ hint_text: t('client.search.placeholder'), style_class: 'llb-search' });
        this._reasons = new ReasonList();
        this._freeText = new St.Entry({ hint_text: t('client.freetext.placeholder'), style_class: 'llb-freetext' });
        this._recent = new RecentTable();
        this._footer = new Footer(t, version);
        this._submitBtn = new St.Button({ label: t('client.button.login'), reactive: true, can_focus: true });
        this._submitBtn.set_reactive(false);
        const logoutBtn = new St.Button({ label: t('client.button.logout.noreason'), reactive: true });

        this._search.clutter_text.connect('text-changed', () =>
            this._reasons.applyFilter(this._search.get_text()));
        this._reasons.connect('selection-changed', (_o, label) => this._select(label));
        this._freeText.clutter_text.connect('text-changed', () => {
            const r = reasonFromFreeText(this._freeText.get_text());
            this._select(r ? r.label : null);
        });
        this._submitBtn.connect('clicked', () => { if (this._selected) onSubmit(this._selected); });
        logoutBtn.connect('clicked', () => onLogout());

        for (const w of [this._logo, this._search, this._reasons, this._freeText,
            this._recent, this._footer, this._submitBtn, logoutBtn])
            card.add_child(w);
        this.add_child(card);
        this._selected = null;
    }
    _buildCovers() {
        for (const m of Main.layoutManager.monitors) {
            const cover = new St.Widget({ style_class: 'llb-cover', reactive: true });
            cover.set_position(m.x, m.y);
            cover.set_size(m.width, m.height);
            this._covers.push(cover);
        }
    }
    getCoverActors() { return this._covers; }
    _select(label) {
        this._selected = label;
        this._submitBtn.set_reactive(!!label);
    }
    setBranding(b) { this._logo.setBranding(b); }
    setLogo(l) { this._logo.setLogo(l); }
    setReasons(list) { this._reasons.populate(list); }
    setRecent(events, days) { this._recent.populate(events, days); }
    setUserHost(u, h) { this._footer.setUserHost(u, h); }
    setStatus(online) { this._footer.setStatus(online); }
    setFreeTextVisible(v) { this._freeText.visible = v; }
    retranslate() { this._footer.retranslate(); this._recent.retranslate(); }
});
```

Add the locale keys used above to **both** `locales/de.json` and `locales/en.json` if missing (keep parity): `client.search.placeholder`, `client.freetext.placeholder`, `client.button.login`, `client.button.logout.noreason`, `client.button.cancel`, `client.dialog.logout.confirm`, `client.status.online`, `client.status.offline`. Reuse the client's existing values where the same key already exists in `loginlogbook-client/app/locales/de.json`; only add genuinely new keys.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — helpers green and **locale parity still green** (new keys added to both files).

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/src/ui/ loginlogbook-gnome-extension/tests/helpers.test.js loginlogbook-gnome-extension/tests/run.js loginlogbook-gnome-extension/locales/
git commit -m "feat(gnome-ext): UI pure helpers (tested) + St widget modules"
```

---

## Task 9: Orchestration in `extension.js` + manual smoke verification

**Files:**
- Modify: `loginlogbook-gnome-extension/extension.js` (full enable/disable wiring)
- Create: `loginlogbook-gnome-extension/README.md` (install + manual smoke checklist)

**Interfaces:**
- Consumes: `loadConfig`, `isUsable` (config.js); `ApiClient` (net.js); `CacheStore`, `EventQueue` (store.js); `Translator` (i18n.js); `ModalGuard` (enforcement.js); `Overlay` (ui/overlay.js); `EventIn` (models.js).
- Produces: a working extension. `enable()` orchestrates: load config → fail-open guard → construct → cache-first paint → grab → async API refresh → submit/logout flows. `disable()` tears everything down.

- [ ] **Step 1: Write `extension.js`**

Replace `extension.js` with:
```javascript
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

import { loadConfig, isUsable } from './src/config.js';
import { ApiClient } from './src/net.js';
import { CacheStore, EventQueue } from './src/store.js';
import { Translator } from './src/i18n.js';
import { ModalGuard } from './src/enforcement.js';
import { Overlay } from './src/ui/overlay.js';
import { EventIn } from './src/models.js';

export default class LoginLogBookExtension extends Extension {
    enable() {
        try {
            const cfg = loadConfig();
            if (!isUsable(cfg)) {
                log('[loginlogbook] no API_URL in /etc/loginlogbook.env — failing open (no grab)');
                return;
            }
            this._start(cfg);
        } catch (e) {
            logError(e, '[loginlogbook] enable failed — failing open');
            this._teardown();
        }
    }

    _start(cfg) {
        const host = GLib.get_host_name();
        const user = GLib.get_user_name();
        this._cache = new CacheStore(cfg.cacheDir);
        this._queue = new EventQueue(cfg.queueFile);
        this._api = new ApiClient(cfg);
        this._t = new Translator(GLib.build_filenamev([this.path, 'locales']));

        this._overlay = new Overlay(this._t.t.bind(this._t), this.metadata.version || '0', {
            onSubmit: (label) => this._submit(cfg, host, user, label),
            onLogout: () => this._logout(),
        });
        this._overlay.setUserHost(user, host);

        // Cover every monitor, then the card overlay, then grab.
        for (const cover of this._overlay.getCoverActors()) Main.layoutManager.addTopChrome(cover);
        Main.layoutManager.addTopChrome(this._overlay);
        this._overlay.set_size(...global.stage.get_size());

        this._guard = new ModalGuard({ Main, actor: this._overlay });
        if (!this._guard.engage()) {
            log('[loginlogbook] could not acquire modal grab — failing open');
            this._teardown();
            return;
        }

        this._paintFromCache();
        this._refresh(host).catch(e => logError(e, '[loginlogbook] refresh failed'));
    }

    _paintFromCache() {
        const reasons = this._cache.loadReasons();
        if (reasons) this._overlay.setReasons(reasons);
        const logo = this._cache.loadLogo();
        if (logo) this._overlay.setLogo(logo);
        const cfg = this._cache.loadConfig();
        this._recentDays = cfg ? cfg.recent_days : 7;
        const recent = this._cache.loadRecent();
        if (recent) this._overlay.setRecent(recent, this._recentDays);
        this._overlay.setStatus(false);
    }

    async _refresh(host) {
        const [reasons, config, branding, settings] = await Promise.all([
            this._api.getReasons(), this._api.getConfig(),
            this._api.getBrandingConfig(), this._api.getSettings(),
        ]);
        this._recentDays = config.recent_days;
        this._t.setLanguage(settings.language);
        this._overlay.retranslate();
        this._overlay.setReasons(reasons);
        this._overlay.setBranding(branding);
        this._overlay.setFreeTextVisible(config.allow_free_text);
        this._cache.saveReasons(reasons);
        this._cache.saveConfig(config);
        try {
            const logo = await this._api.getLogo();
            this._overlay.setLogo(logo);
            this._cache.saveLogo(logo.data, logo.contentType);
        } catch (e) { logError(e, '[loginlogbook] logo fetch failed'); }
        try {
            const recent = await this._api.getRecentEvents(host, this._recentDays);
            this._overlay.setRecent(recent, this._recentDays);
            this._cache.saveRecent(recent);
        } catch (e) { logError(e, '[loginlogbook] recent fetch failed'); }
        this._overlay.setStatus(true);
    }

    async _submit(cfg, host, user, label) {
        const evt = EventIn({
            event_type: 'login', host, os_user: user, reason: label,
            timestamp: GLib.DateTime.new_now_local().format_iso8601(),
        });
        try { await this._api.postEvent(evt); }
        catch (e) { logError(e, '[loginlogbook] post failed — queued'); this._queue.enqueue(evt); }
        try { await this._queue.flush(e => this._api.postEvent(e)); } catch { /* keep for later */ }
        this._teardown();
    }

    _logout() {
        const sid = GLib.getenv('XDG_SESSION_ID');
        const argv = sid
            ? ['loginctl', 'terminate-session', sid]
            : ['pkill', '-KILL', '-u', GLib.get_user_name()];
        try { Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE); }
        catch (e) { logError(e, '[loginlogbook] logout failed'); }
    }

    disable() { this._teardown(); }

    _teardown() {
        if (this._guard) { this._guard.release(); this._guard = null; }
        if (this._overlay) {
            for (const cover of this._overlay.getCoverActors()) cover.destroy();
            this._overlay.destroy();
            this._overlay = null;
        }
        this._api = null; this._cache = null; this._queue = null; this._t = null;
    }
}
```

- [ ] **Step 2: Verify the unit suite still passes (no regressions)**

Run: `cd loginlogbook-gnome-extension && gjs -m tests/run.js`
Expected: PASS — all headless tests green (extension.js is not imported by the suite; this confirms nothing else broke).

- [ ] **Step 3: Install into the live session for manual smoke**

Run (uses the packaging script from Task 10 — do Task 10 first, or link manually):
```bash
ln -sfn "$PWD/loginlogbook-gnome-extension" ~/.local/share/gnome-shell/extensions/loginlogbook@ozon08.github.io
gnome-extensions enable loginlogbook@ozon08.github.io
```
Then log out and back in (Wayland cannot live-reload the shell).

- [ ] **Step 4: Run the manual smoke checklist**

With `/etc/loginlogbook.env` present and the API reachable, confirm each:
1. After login, the overlay covers **all** monitors.
2. Super, Alt+Tab, Activities/Overview, and workspace-switch shortcuts are blocked.
3. Stop the API (`docker compose stop api`) and log in again → cached reasons/logo shown, footer offline; picking a reason still closes the overlay and the event lands in the queue file.
4. With the API up, pick a reason → overlay releases, desktop is free, the event appears in InfluxDB/Grafana.
5. Click *Abmelden* → confirm → the session terminates.
6. Rename `/etc/loginlogbook.env` away → log in → **no grab**, desktop is immediately usable (fail-open). Check `journalctl --user -b | grep loginlogbook` shows the fail-open log line.
7. `journalctl --user -b -g loginlogbook` shows no unhandled exceptions.

Record the results in the README smoke table (Step 5).

- [ ] **Step 5: Write `README.md` with install + smoke checklist, then commit**

Create `loginlogbook-gnome-extension/README.md` documenting: purpose, GNOME 50 requirement, `gjs -m tests/run.js` for unit tests, `packaging/install.sh` for enforced install, the fail-open behavior, the VT-switch residual gap, and the 7-point manual smoke checklist from Step 4.

```bash
git add loginlogbook-gnome-extension/extension.js loginlogbook-gnome-extension/README.md
git commit -m "feat(gnome-ext): enable/disable orchestration + manual smoke docs"
```

---

## Task 10: Packaging — enforced install/uninstall

**Files:**
- Create: `loginlogbook-gnome-extension/packaging/install.sh`
- Create: `loginlogbook-gnome-extension/packaging/uninstall.sh`
- Create: `loginlogbook-gnome-extension/packaging/install.test.sh`

**Interfaces:**
- Produces: `install.sh` copies the extension to `${DESTDIR}/usr/share/gnome-shell/extensions/loginlogbook@ozon08.github.io/`, writes a dconf default + lock enabling the UUID under `${DESTDIR}/etc/dconf/db/local.d/`, and runs `dconf update` (skipped when `DESTDIR` is set). `DESTDIR` supports offline/testable dry runs. `uninstall.sh` reverses it.

- [ ] **Step 1: Write the failing test**

Create `packaging/install.test.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(mktemp -d)"
DESTDIR="$root" "$here/install.sh"
ext="$root/usr/share/gnome-shell/extensions/loginlogbook@ozon08.github.io"
test -f "$ext/metadata.json" || { echo "FAIL: metadata not installed"; exit 1; }
test -f "$ext/extension.js" || { echo "FAIL: extension.js not installed"; exit 1; }
grep -q "loginlogbook@ozon08.github.io" "$root/etc/dconf/db/local.d/00-loginlogbook" || { echo "FAIL: dconf default missing"; exit 1; }
grep -q "enabled-extensions" "$root/etc/dconf/db/local.d/locks/loginlogbook" || { echo "FAIL: dconf lock missing"; exit 1; }
echo "PASS"
```

Make it executable: `chmod +x packaging/install.test.sh`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd loginlogbook-gnome-extension && bash packaging/install.test.sh`
Expected: FAIL — `install.sh` does not exist / not executable.

- [ ] **Step 3: Write minimal implementation**

Create `packaging/install.sh`:
```bash
#!/usr/bin/env bash
# Install the LoginLogBook GNOME extension system-wide and force-enable it via
# dconf. Set DESTDIR for a staged/dry-run install (skips `dconf update`).
set -euo pipefail
UUID="loginlogbook@ozon08.github.io"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DESTDIR="${DESTDIR:-}"

extdir="${DESTDIR}/usr/share/gnome-shell/extensions/${UUID}"
mkdir -p "$extdir"
cp -r "$SRC/metadata.json" "$SRC/extension.js" "$SRC/src" "$SRC/locales" "$extdir/"

dconfdir="${DESTDIR}/etc/dconf/db/local.d"
mkdir -p "$dconfdir/locks"
cat > "$dconfdir/00-loginlogbook" <<EOF
[org/gnome/shell]
enabled-extensions=['${UUID}']
EOF
cat > "$dconfdir/locks/loginlogbook" <<EOF
/org/gnome/shell/enabled-extensions
EOF

if [ -z "$DESTDIR" ]; then
    dconf update
    echo "Installed and enforced ${UUID}. Users must re-login to apply."
else
    echo "Staged install under ${DESTDIR} (dconf update skipped)."
fi
```

Create `packaging/uninstall.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
UUID="loginlogbook@ozon08.github.io"
DESTDIR="${DESTDIR:-}"
rm -rf "${DESTDIR}/usr/share/gnome-shell/extensions/${UUID}"
rm -f "${DESTDIR}/etc/dconf/db/local.d/00-loginlogbook"
rm -f "${DESTDIR}/etc/dconf/db/local.d/locks/loginlogbook"
if [ -z "$DESTDIR" ]; then dconf update; fi
echo "Removed ${UUID}."
```

Make both executable: `chmod +x packaging/install.sh packaging/uninstall.sh`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd loginlogbook-gnome-extension && bash packaging/install.test.sh`
Expected: `PASS`.

Optional lint: `shellcheck packaging/*.sh` (no errors).

- [ ] **Step 5: Commit**

```bash
git add loginlogbook-gnome-extension/packaging/
git commit -m "feat(gnome-ext): enforced system install/uninstall via dconf"
```

---

## Task 11: Retire the dead X11 lock code in the PyQt client

**Files:**
- Modify: `loginlogbook-client/app/platform_linux.py`
- Modify: `loginlogbook-client/README.md` or root `README.md` (note Wayland enforcement lives in the extension)

**Interfaces:**
- The spec records that `lock()`/`unlock()`/`setup_fullscreen()` are dead code. X11 enforcement is out of scope here (tracked as #18); this task only removes the misleading Wayland branch and documents where Wayland enforcement now lives — it does not add new behavior.

- [ ] **Step 1: Remove the misleading Wayland branch in `setup_fullscreen`**

In `loginlogbook-client/app/platform_linux.py`, replace the body of `setup_fullscreen` so it no longer forces `QT_QPA_PLATFORM=xcb` (which conflicts with `__main__.py` setting `wayland` and never took effect):
```python
def setup_fullscreen(window) -> None:
    # No-op: input confinement on Wayland is handled by the GNOME Shell
    # extension (loginlogbook-gnome-extension), not by the Qt client.
    # On X11 the keyboard grab in lock() applies (see task #18).
    return
```

- [ ] **Step 2: Run the client test suite to confirm no regression**

Run: `cd loginlogbook-client && uv run pytest -q`
Expected: PASS — existing tests still green (the platform tests monkeypatch these functions; the no-op change is compatible).

- [ ] **Step 3: Document where Wayland enforcement lives**

Add a short note to the root `README.md` near the client/architecture section: under GNOME/Wayland, desktop enforcement is provided by `loginlogbook-gnome-extension` (a GNOME Shell extension), while the PyQt client remains the overlay for X11 and Windows.

- [ ] **Step 4: Commit**

```bash
git add loginlogbook-client/app/platform_linux.py README.md
git commit -m "refactor(client): drop dead Wayland xcb branch; point to shell extension"
```

---

## Self-Review Notes

- **Spec coverage:** module layout (Task 1–8), lifecycle/enable-disable (Task 9), enforcement/pushModal + monitor covers (Task 7/9), config from env with defaults (Task 2), API contract incl. `X-Client-Token`/5 s (Task 5), cache+queue parity (Task 4), i18n + parity test (Task 6), UI parity widgets (Task 8), fail-open at every failure point (Task 2/9), test strategy headless + manual checklist (all tasks + Task 9), packaging with dconf lock (Task 10), documented VT-switch residual gap (Task 9 README). The dead-code note in the spec is actioned in Task 11.
- **`reason` value:** the client submits `reason.label` (verified in `overlay_window.py`); the extension submits the selected reason's `label` or the trimmed free text — consistent across Task 8 (`reasonFromFreeText`) and Task 9 (`_submit`).
- **Type consistency:** transport shape `{status, bytes, headers}`, `getLogo()→{data,contentType}`, `ModalGuard.engage()/release()/isActive()`, `Overlay.set*` methods, and `EventIn` fields are used identically across Tasks 5, 7, 8, 9.
- **Async harness:** introduced in Task 4 (`runAll`) before the first async test; all later suites rely on it.
