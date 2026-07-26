import GLib from 'gi://GLib';
import { test, assertEqual } from './harness.js';

function localesDir() {
    const testsDir = GLib.path_get_dirname(import.meta.url.replace('file://', ''));
    return GLib.build_filenamev([GLib.path_get_dirname(testsDir), 'locales']);
}
function keys(name) {
    const [, bytes] = GLib.file_get_contents(GLib.build_filenamev([localesDir(), name]));
    return Object.keys(JSON.parse(new TextDecoder().decode(bytes))).sort();
}

test('en.json has the same keys as de.json', () => {
    assertEqual(keys('en.json'), keys('de.json'), 'parity en vs de');
});
