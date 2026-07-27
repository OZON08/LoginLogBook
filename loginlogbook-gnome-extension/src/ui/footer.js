import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';

export const Footer = GObject.registerClass(class Footer extends St.BoxLayout {
    _init(t, version) {
        super._init({ style_class: 'llb-footer' });
        this._t = t;
        this._userHost = new St.Label({ text: '', style_class: 'llb-footer-item' });
        this._license = new St.Label({
            text: `© 2026 OZON08 · MIT License · v${version}`,
            style_class: 'llb-footer-license', x_expand: true,
            x_align: Clutter.ActorAlign.CENTER });
        this._status = new St.Label({ text: '', style_class: 'llb-status' });
        this.add_child(this._userHost);
        this.add_child(this._license);
        this.add_child(this._status);
    }
    setUserHost(user, host) { this._userHost.text = `${user} · ${host}`; }
    setStatus(online) {
        this._status.text = this._t(online ? 'client.footer.status.online' : 'client.footer.status.offline');
        this._status.remove_style_class_name(online ? 'llb-status-offline' : 'llb-status-online');
        this._status.add_style_class_name(online ? 'llb-status-online' : 'llb-status-offline');
    }
    retranslate() { /* status re-set by caller via setStatus */ }
});
