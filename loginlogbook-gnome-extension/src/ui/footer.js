import GObject from 'gi://GObject';
import St from 'gi://St';

export const Footer = GObject.registerClass(class Footer extends St.BoxLayout {
    _init(t, version) {
        super._init({ style_class: 'llb-footer' });
        this._t = t;
        this._userHost = new St.Label({ text: '' });
        this._status = new St.Label({ text: '' });
        this._version = new St.Label({ text: `v${version}` });
        this.add_child(this._userHost);
        this.add_child(this._status);
        this.add_child(this._version);
    }
    setUserHost(user, host) { this._userHost.text = `${user}@${host}`; }
    setStatus(online) {
        this._status.text = this._t(online ? 'client.footer.status.online' : 'client.footer.status.offline');
    }
    retranslate() { /* status re-set by caller via setStatus */ }
});
