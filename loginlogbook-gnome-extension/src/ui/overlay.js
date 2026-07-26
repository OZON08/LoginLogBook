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
        this._search = new St.Entry({ hint_text: t('client.reason.search.placeholder'), style_class: 'llb-search' });
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
