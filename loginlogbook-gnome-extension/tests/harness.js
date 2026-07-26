// Minimal pure-gjs assert runner. No external deps.
const _results = [];
export function test(name, fn) {
    try { fn(); _results.push([true, name, '']); }
    catch (e) { _results.push([false, name, String(e && e.message || e)]); }
}
export function assertEqual(actual, expected, msg = '') {
    const a = JSON.stringify(actual), b = JSON.stringify(expected);
    if (a !== b) throw new Error(`${msg}: ${a} !== ${b}`);
}
export function assertThrows(fn, msg = '') {
    let threw = false;
    try { fn(); } catch { threw = true; }
    if (!threw) throw new Error(`${msg}: expected throw`);
}
export function report() {
    let failed = 0;
    for (const [ok, name, err] of _results) {
        print(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok ? '' : ' — ' + err}`);
        if (!ok) failed++;
    }
    print(`\n${_results.length - failed}/${_results.length} passed`);
    return failed === 0 ? 0 : 1;
}
