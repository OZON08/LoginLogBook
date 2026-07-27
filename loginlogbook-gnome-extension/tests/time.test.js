import GLib from 'gi://GLib';
import { test, assertEqual } from './harness.js';
import { rfc3339 } from '../src/time.js';

// Regression: GLib's format_iso8601() emits an abbreviated, colon-less offset
// ("...+02"), which the API's pydantic datetime parser rejects with 422
// ("unexpected extra characters at the end of the input"). rfc3339 must emit
// the full "+02:00" offset.
test('rfc3339 emits a colon-separated timezone offset', () => {
    const tz = GLib.TimeZone.new_identifier('+02:00');
    const dt = GLib.DateTime.new(tz, 2026, 7, 27, 8, 3, 53);
    assertEqual(rfc3339(dt), '2026-07-27T08:03:53+02:00');
});

test('rfc3339 handles UTC as +00:00', () => {
    const tz = GLib.TimeZone.new_identifier('UTC');
    const dt = GLib.DateTime.new(tz, 2026, 1, 2, 3, 4, 5);
    assertEqual(rfc3339(dt), '2026-01-02T03:04:05+00:00');
});
