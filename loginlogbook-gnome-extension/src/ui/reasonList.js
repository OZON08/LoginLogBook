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
