import GLib from 'gi://GLib';
import { test, assertEqual } from './harness.js';

function extDir() {
    const testsDir = GLib.path_get_dirname(import.meta.url.replace('file://', ''));
    return GLib.path_get_dirname(testsDir); // extension root
}
function readText(path) {
    const [ok, bytes] = GLib.file_get_contents(path);
    if (!ok) throw new Error('cannot read ' + path);
    return new TextDecoder().decode(bytes);
}
function jsFiles(dir, acc = []) {
    const d = GLib.Dir.open(dir, 0);
    let name;
    while ((name = d.read_name()) !== null) {
        const full = GLib.build_filenamev([dir, name]);
        if (GLib.file_test(full, GLib.FileTest.IS_DIR)) jsFiles(full, acc);
        else if (name.endsWith('.js')) acc.push(full);
    }
    d.close();
    return acc;
}
// Every llb-* class referenced via style_class / styleClass in the code.
function usedClasses() {
    const root = extDir();
    const files = jsFiles(GLib.build_filenamev([root, 'src']));
    files.push(GLib.build_filenamev([root, 'extension.js']));
    const re = /style(?:_class|Class):\s*'(llb-[a-z0-9-]+)'/g;
    const set = new Set();
    for (const f of files) {
        const src = readText(f);
        let m;
        while ((m = re.exec(src)) !== null) set.add(m[1]);
    }
    return [...set].sort();
}

test('stylesheet.css defines every llb-* class used in code', () => {
    const css = readText(GLib.build_filenamev([extDir(), 'stylesheet.css']));
    const missing = usedClasses().filter(c => !css.includes('.' + c));
    assertEqual(missing, [], 'style classes with no selector in stylesheet.css');
});
