import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import { test, assertEqual } from './harness.js';
import { Translator } from '../src/i18n.js';

function fixtureDir() {
    const d = GLib.build_filenamev([GLib.get_tmp_dir(), 'llb-loc-' + Math.random().toString(36).slice(2)]);
    Gio.File.new_for_path(d).make_directory_with_parents(null);
    const write = (n, o) => Gio.File.new_for_path(GLib.build_filenamev([d, n]))
        .replace_contents(new TextEncoder().encode(JSON.stringify(o)), null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, null);
    write('de.json', { greet: 'Hallo {name}', only_de: 'DE' });
    write('en.json', { greet: 'Hello {name}' });
    return d;
}

test('t interpolates and falls back active -> de -> key', () => {
    const tr = new Translator(fixtureDir());
    tr.setLanguage('en');
    assertEqual(tr.t('greet', { name: 'X' }), 'Hello X', 'active');
    assertEqual(tr.t('only_de'), 'DE', 'fallback to de');
    assertEqual(tr.t('missing'), 'missing', 'fallback to key');
});
test('available lists sorted stems', () => {
    assertEqual(new Translator(fixtureDir()).available(), ['de', 'en'], 'available');
});
