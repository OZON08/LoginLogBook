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
