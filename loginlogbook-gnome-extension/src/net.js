import GLib from 'gi://GLib';
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
