import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import { test, assertEqual } from './harness.js';
import { CacheStore, EventQueue } from '../src/store.js';

function tmpdir() {
    const d = GLib.build_filenamev([GLib.get_tmp_dir(), 'llb-' + Math.random().toString(36).slice(2)]);
    Gio.File.new_for_path(d).make_directory_with_parents(null);
    return d;
}

test('CacheStore round-trips reasons and returns null when absent', () => {
    const c = new CacheStore(tmpdir());
    assertEqual(c.loadReasons(), null, 'absent');
    c.saveReasons([{ id: 'a', label: 'A', active: true }]);
    assertEqual(c.loadReasons(), [{ id: 'a', label: 'A', active: true }], 'roundtrip');
});

test('EventQueue enqueue/flush keeps failures', async () => {
    const q = new EventQueue(GLib.build_filenamev([tmpdir(), 'queue.json']));
    q.enqueue({ event_type: 'login', host: 'h', os_user: 'u', reason: 'r', timestamp: 't' });
    q.enqueue({ event_type: 'login', host: 'h', os_user: 'u', reason: 's', timestamp: 't' });
    assertEqual(q.pendingCount(), 2, 'two pending');
    let calls = 0;
    const sent = await q.flush(async (e) => { calls++; if (e.reason === 's') throw new Error('fail'); });
    assertEqual(sent, 1, 'one sent');
    assertEqual(q.pendingCount(), 1, 'one kept');
});
