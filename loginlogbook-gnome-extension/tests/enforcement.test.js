import { test, assertEqual } from './harness.js';
import { monitorCovers, ModalGuard } from '../src/enforcement.js';

test('monitorCovers yields one full rect per monitor', () => {
    const covers = monitorCovers([{ x: 0, y: 0, width: 1920, height: 1080 }, { x: 1920, y: 0, width: 1280, height: 1024 }]);
    assertEqual(covers, [{ x: 0, y: 0, width: 1920, height: 1080 }, { x: 1920, y: 0, width: 1280, height: 1024 }], 'covers');
});

test('ModalGuard engage/release is idempotent', () => {
    let pushes = 0, pops = 0;
    const fakeMain = {
        pushModal: () => { pushes++; return { _grab: true }; },
        popModal: () => { pops++; },
    };
    const g = new ModalGuard({ Main: fakeMain, actor: {} });
    assertEqual(g.engage(), true, 'engaged');
    assertEqual(g.isActive(), true, 'active');
    g.release(); g.release();
    assertEqual(pushes, 1, 'one push');
    assertEqual(pops, 1, 'one pop despite double release');
    assertEqual(g.isActive(), false, 'inactive');
});
