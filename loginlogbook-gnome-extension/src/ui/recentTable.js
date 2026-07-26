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
