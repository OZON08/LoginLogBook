import GLib from 'gi://GLib';
import { test, assertEqual } from './harness.js';

function readJson(rel) {
    const dir = GLib.path_get_dirname(GLib.path_get_dirname(import.meta.url.replace('file://', '')));
    const [ok, bytes] = GLib.file_get_contents(GLib.build_filenamev([dir, rel]));
    void ok;
    return JSON.parse(new TextDecoder().decode(bytes));
}

test('metadata has correct uuid', () => {
    assertEqual(readJson('metadata.json').uuid, 'loginlogbook@ozon08.github.io', 'uuid');
});
test('metadata targets shell 50', () => {
    assertEqual(readJson('metadata.json')['shell-version'], ['50'], 'shell-version');
});
