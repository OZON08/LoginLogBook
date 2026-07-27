import GObject from 'gi://GObject';
import St from 'gi://St';
import { withinDays } from './helpers.js';

export const RecentTable = GObject.registerClass(class RecentTable extends St.BoxLayout {
    _init(t) {
        super._init({ vertical: true, style_class: 'llb-recent' });
        this._t = t;
        this._days = 0;
        this._title = new St.Label({ text: t('client.recent.title'), style_class: 'llb-recent-title' });
        this._daysLabel = new St.Label({ text: '', style_class: 'llb-recent-days' });
        this._rows = new St.BoxLayout({ vertical: true, style_class: 'llb-recent-rows' });
        this.add_child(this._title);
        this.add_child(this._daysLabel);
        this.add_child(this._rows);
    }
    populate(events, days) {
        this._days = days;
        this._daysLabel.text = this._t('client.recent.days', { days });
        this._rows.destroy_all_children();
        const list = withinDays(events || [], days, Date.now())
            .slice().sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
        if (list.length === 0) {
            this._rows.add_child(new St.Label({
                text: this._t('client.recent.empty'), style_class: 'llb-recent-empty' }));
            return;
        }
        for (const e of list) {
            const row = new St.BoxLayout({ style_class: 'llb-recent-row' });
            const ts = String(e.timestamp).replace('T', ' ').slice(0, 16);
            const tsCell = new St.Label({ text: ts, style_class: 'llb-recent-cell' });
            tsCell.style = 'min-width: 130px;';
            const userCell = new St.Label({ text: e.os_user || '', style_class: 'llb-recent-cell' });
            userCell.style = 'min-width: 90px;';
            const reasonCell = new St.Label({ text: e.reason || '', style_class: 'llb-recent-cell', x_expand: true });
            row.add_child(tsCell);
            row.add_child(userCell);
            row.add_child(reasonCell);
            this._rows.add_child(row);
        }
    }
    retranslate() {
        this._title.text = this._t('client.recent.title');
        if (this._days) this._daysLabel.text = this._t('client.recent.days', { days: this._days });
    }
});
