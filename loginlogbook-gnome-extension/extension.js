import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

export default class LoginLogBookExtension extends Extension {
    enable() {
        // Full orchestration is wired in Task 9. Fail-open by construction:
        // any error here must never leave the user locked out.
        try {
            log('[loginlogbook] enable(): skeleton — no guard yet');
        } catch (e) {
            logError(e, '[loginlogbook] enable failed — failing open');
        }
    }

    disable() {
        log('[loginlogbook] disable()');
    }
}
