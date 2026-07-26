import { test, assertEqual, assertThrows } from './harness.js';
import { Reason, EventIn, AppConfig, BrandingConfig, LanguageSetting, safeLogoBg } from '../src/models.js';

test('Reason defaults active=true', () => {
    assertEqual(Reason({ id: 'a', label: 'A' }), { id: 'a', label: 'A', active: true }, 'reason');
});
test('EventIn builds wire body and defaults reason=null', () => {
    const e = EventIn({ event_type: 'login', host: 'h', os_user: 'u', timestamp: '2026-07-20T10:00:00' });
    assertEqual(e, { event_type: 'login', host: 'h', os_user: 'u', reason: null, timestamp: '2026-07-20T10:00:00' }, 'eventin');
});
test('EventIn rejects bad event_type', () => {
    assertThrows(() => EventIn({ event_type: 'nope', host: 'h', os_user: 'u', timestamp: 't' }), 'bad type');
});
test('EventIn rejects missing host', () => {
    assertThrows(() => EventIn({ event_type: 'login', os_user: 'u', timestamp: 't' }), 'missing host');
});
test('defaults for config models', () => {
    assertEqual(AppConfig({}), { recent_days: 7, allow_free_text: true }, 'appconfig');
    assertEqual(BrandingConfig({}), { logo_height: 120, logo_bg: '#1E293B' }, 'branding');
    assertEqual(LanguageSetting({}), { language: 'de', available: [] }, 'language');
});
test('safeLogoBg validates hex', () => {
    assertEqual(safeLogoBg('#AbC123'), '#AbC123', 'valid');
    assertEqual(safeLogoBg('red'), '#1E293B', 'invalid');
});
