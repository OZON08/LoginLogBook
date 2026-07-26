import GObject from 'gi://GObject';
import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import { safeLogoBg } from '../models.js';

export const Logo = GObject.registerClass(class Logo extends St.Bin {
    _init() {
        super._init({ style_class: 'llb-logo', x_align: Clutter.ActorAlign.CENTER });
        this._img = new St.Icon({ icon_size: 96 });
        this.set_child(this._img);
    }
    setBranding(branding) {
        this.style = `background-color: ${safeLogoBg(branding.logo_bg)}; padding: 16px;`;
        this._img.icon_size = branding.logo_height || 120;
    }
    // Write bytes to a temp file and load as a file icon (avoids GdkPixbuf dep).
    setLogo({ data }) {
        const path = GLib.build_filenamev([GLib.get_tmp_dir(), 'llb-logo.bin']);
        Gio.File.new_for_path(path).replace_contents(
            data, null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        this._img.gicon = Gio.FileIcon.new(Gio.File.new_for_path(path));
    }
});
