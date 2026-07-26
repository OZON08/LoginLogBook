// Shell.ActionMode.SYSTEM_MODAL === 1 << 11 in GNOME Shell. Kept as a literal
// so this module never needs the Shell typelib at unit-test time.
const SYSTEM_MODAL = 1 << 11;

export function monitorCovers(monitors) {
    return monitors.map(m => ({ x: m.x, y: m.y, width: m.width, height: m.height }));
}

export class ModalGuard {
    constructor({ Main, actor }) {
        this._Main = Main;
        this._actor = actor;
        this._grab = null;
        this._active = false;
    }
    engage() {
        if (this._active) return true;
        this._grab = this._Main.pushModal(this._actor, { actionMode: SYSTEM_MODAL });
        this._active = !!this._grab;
        return this._active;
    }
    release() {
        if (!this._active) return;
        this._Main.popModal(this._grab || this._actor);
        this._grab = null;
        this._active = false;
    }
    isActive() { return this._active; }
}
