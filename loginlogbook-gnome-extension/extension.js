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
