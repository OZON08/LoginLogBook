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
