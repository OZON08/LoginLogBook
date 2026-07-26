import { test, assertEqual } from './harness.js';
import { filterReasons, withinDays, reasonFromFreeText } from '../src/ui/helpers.js';

const reasons = [
    { id: '1', label: 'Wartung', active: true },
    { id: '2', label: 'Update', active: true },
    { id: '3', label: 'Alt', active: false },
];

test('filterReasons: empty query returns active only', () => {
    assertEqual(filterReasons(reasons, ''), [reasons[0], reasons[1]], 'active only');
});
test('filterReasons: case-insensitive substring', () => {
    assertEqual(filterReasons(reasons, 'up'), [reasons[1]], 'match update');
});
test('withinDays keeps recent, drops old', () => {
    const now = Date.parse('2026-07-20T12:00:00Z');
    const evs = [
        { timestamp: '2026-07-19T12:00:00Z', host: 'h', os_user: 'u', event_type: 'login', reason: null },
        { timestamp: '2026-07-01T12:00:00Z', host: 'h', os_user: 'u', event_type: 'login', reason: null },
    ];
    assertEqual(withinDays(evs, 7, now).length, 1, 'one within 7 days');
});
test('reasonFromFreeText trims and rejects blank', () => {
    assertEqual(reasonFromFreeText('  Hallo '), { id: '', label: 'Hallo', active: true }, 'trim');
    assertEqual(reasonFromFreeText('   '), null, 'blank');
});
