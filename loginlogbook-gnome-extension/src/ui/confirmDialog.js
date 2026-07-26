import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';

export const ConfirmDialog = GObject.registerClass(class ConfirmDialog extends ModalDialog.ModalDialog {
    _init(t, onConfirm) {
        super._init({ styleClass: 'llb-confirm' });
        this.contentLayout.add_child(new St.Label({ text: t('client.confirm.logout.question') }));
        this.setButtons([
            { label: t('client.confirm.cancel'), action: () => this.close(), key: Clutter.KEY_Escape },
            { label: t('client.button.logout.noreason'), action: () => { this.close(); onConfirm(); } },
        ]);
    }
});
