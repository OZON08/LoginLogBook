import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Logo } from './logo.js';
import { ReasonList } from './reasonList.js';
import { RecentTable } from './recentTable.js';
import { Footer } from './footer.js';
import { reasonFromFreeText } from './helpers.js';

// Mirrors the PyQt client's layout: a fixed-width card with a centred logo on
// top, a two-column body (left = search + reason list + free text + actions,
// right = recent-events table, split by a vertical divider), and a footer.
export const Overlay = GObject.registerClass(class Overlay extends St.Widget {
    _init(t, version, { onSubmit, onLogout }) {
        super._init({ style_class: 'llb-overlay', reactive: true,
            layout_manager: new Clutter.BinLayout() });
        this._t = t;
        this._onSubmit = onSubmit;
        this._covers = [];
        this._buildCovers();

        const card = new St.BoxLayout({ vertical: true, style_class: 'llb-card',
            x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER });

        this._logo = new Logo();

        // ---- left column ----
        this._search = new St.Entry({ hint_text: t('client.reason.search.placeholder'),
            style_class: 'llb-search', x_expand: true });
        this._reasons = new ReasonList();
        this._orLabel = new St.Label({ text: t('client.freetext.or'), style_class: 'llb-or',
            x_align: Clutter.ActorAlign.CENTER });
        this._freeText = new St.Entry({ hint_text: t('client.freetext.placeholder'),
            style_class: 'llb-freetext', x_expand: true });

        this._submitBtn = new St.Button({ label: t('client.button.login'),
            can_focus: true, style_class: 'llb-submit', x_expand: true });
        const logoutBtn = new St.Button({ label: t('client.button.logout'),
            reactive: true, style_class: 'llb-logout', x_expand: true });
        const buttons = new St.BoxLayout({ style_class: 'llb-buttons' });
        buttons.add_child(logoutBtn);
        buttons.add_child(this._submitBtn);

        const left = new St.BoxLayout({ vertical: true, style_class: 'llb-col-left', x_expand: true });
        left.add_child(this._search);
        left.add_child(this._reasons);
        left.add_child(this._orLabel);
        left.add_child(this._freeText);
        left.add_child(new St.Widget({ style_class: 'llb-spacer', y_expand: true }));
        left.add_child(buttons);

        const divider = new St.Widget({ style_class: 'llb-divider', y_expand: true });

        // ---- right column ----
        this._recent = new RecentTable(t);
        const right = new St.BoxLayout({ vertical: true, style_class: 'llb-col-right', x_expand: true });
        right.add_child(this._recent);

        const columns = new St.BoxLayout({ style_class: 'llb-columns', x_expand: true });
        columns.add_child(left);
        columns.add_child(divider);
        columns.add_child(right);

        this._footer = new Footer(t, version);

        card.add_child(this._logo);
        card.add_child(columns);
        card.add_child(this._footer);
        this.add_child(card);

        // ---- wiring ----
        this._search.clutter_text.connect('text-changed', () =>
            this._reasons.applyFilter(this._search.get_text()));
        this._reasons.connect('selection-changed', (_o, label) => this._select(label));
        this._freeText.clutter_text.connect('text-changed', () => {
            const r = reasonFromFreeText(this._freeText.get_text());
            this._select(r ? r.label : null);
        });
        this._submitBtn.connect('clicked', () => { if (this._selected) onSubmit(this._selected); });
        logoutBtn.connect('clicked', () => onLogout());

        this._selected = null;
        this._select(null);
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
        if (label) this._submitBtn.remove_style_class_name('llb-submit-disabled');
        else this._submitBtn.add_style_class_name('llb-submit-disabled');
    }
    setBranding(b) { this._logo.setBranding(b); }
    setLogo(l) { this._logo.setLogo(l); }
    setReasons(list) { this._reasons.populate(list); }
    setRecent(events, days) { this._recent.populate(events, days); }
    setUserHost(u, h) { this._footer.setUserHost(u, h); }
    setStatus(online) { this._footer.setStatus(online); }
    setFreeTextVisible(v) { this._freeText.visible = v; this._orLabel.visible = v; }
    retranslate() {
        this._footer.retranslate();
        this._recent.retranslate();
        this._orLabel.text = this._t('client.freetext.or');
    }
});
