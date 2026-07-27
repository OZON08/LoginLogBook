import GObject from 'gi://GObject';
import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import Cogl from 'gi://Cogl';
import Clutter from 'gi://Clutter';
import { safeLogoBg } from '../models.js';

export const Logo = GObject.registerClass(class Logo extends St.Bin {
    _init() {
        super._init({ style_class: 'llb-logo', x_align: Clutter.ActorAlign.CENTER });
        this._height = 120;
        this._path = null;
        this._img = new St.Widget({ style_class: 'llb-logo-img',
            x_align: Clutter.ActorAlign.CENTER });
        // Preserve aspect ratio no matter how the parent allocates the actor.
        this._img.set_content_gravity(Clutter.ContentGravity.RESIZE_ASPECT);
        this.set_child(this._img);
    }
    setBranding(branding) {
        this._height = branding.logo_height || 120;
        this.style = `background-color: ${safeLogoBg(branding.logo_bg)}; padding: 16px;`;
        if (this._path) this._applyImage();
    }
    // Persist bytes to a per-user cache file (0600). We deliberately avoid the
    // shared /tmp with a predictable name (local symlink/clobber attack).
    setLogo({ data }) {
        const dir = GLib.build_filenamev([GLib.get_user_cache_dir(), 'loginlogbook']);
        const dirFile = Gio.File.new_for_path(dir);
        if (!dirFile.query_exists(null)) dirFile.make_directory_with_parents(null);
        const path = GLib.build_filenamev([dir, 'logo.bin']);
        Gio.File.new_for_path(path).replace_contents(
            data, null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION | Gio.FileCreateFlags.PRIVATE, null);
        this._path = path;
        this._applyImage();
    }
    _applyImage() {
        // Keep the natural aspect ratio: logical width derived from the source.
        let wLogical = this._height;
        try {
            // Rasterise the source at the EXACT device pixel size the logo will
            // occupy (logical height × display scale factor) and hand St a real
            // GPU texture. Matching texture px to device px means St draws it 1:1
            // — no up/downscaling, so it stays crisp. (A CSS background-image is
            // baked at logical size and then scaled by the compositor → blurry.)
            let scaleFactor = 1;
            try {
                const sf = St.ThemeContext.get_for_stage(global.stage).scale_factor;
                if (sf > 0) scaleFactor = sf;
            } catch { /* not in a shell (tests) */ }
            const deviceH = Math.max(this._height, Math.round(this._height * scaleFactor));
            let pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(this._path, -1, deviceH, true);
            if (!pb.get_has_alpha()) pb = pb.add_alpha(false, 0, 0, 0);
            const texW = pb.get_width(), texH = pb.get_height();
            if (texH > 0) wLogical = Math.round((this._height * texW) / texH);

            const coglContext = Clutter.get_default_backend().get_cogl_context();
            const content = St.ImageContent.new_with_preferred_size(wLogical, this._height);
            // Signature: set_bytes(cogl_context, data, pixel_format, w, h, row_stride).
            content.set_bytes(coglContext, pb.read_pixel_bytes(), Cogl.PixelFormat.RGBA_8888,
                texW, texH, pb.get_rowstride());
            this._img.set_content(content);
            // St.Widget does not size itself from the content, so force the box.
            this._img.style =
                `width: ${wLogical}px; height: ${this._height}px; ` +
                `min-width: ${wLogical}px; min-height: ${this._height}px;`;
            this._img.set_size(wLogical, this._height);
            return;
        } catch (e) {
            logError(e, '[loginlogbook] logo texture failed');
        }
        // Fallback: CSS background-image at the correct (non-square) box — softer
        // on HiDPI but always renders at the right size.
        this._img.set_content(null);
        this._img.style =
            `background-image: url("${this._path}"); background-size: contain; ` +
            `background-repeat: no-repeat; ` +
            `width: ${wLogical}px; height: ${this._height}px; ` +
            `min-width: ${wLogical}px; min-height: ${this._height}px;`;
    }
});
