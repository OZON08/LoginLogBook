import { test, assertEqual } from './harness.js';
import { ApiClient } from '../src/net.js';

function recorder(responses) {
    const calls = [];
    const transport = async ({ method, url, headers, body }) => {
        calls.push({ method, url, headers, body });
        const r = responses.shift();
        return { status: r.status, bytes: new TextEncoder().encode(r.text || ''), headers: r.headers || {} };
    };
    return { transport, calls };
}

test('getReasons sends token header and parses list', async () => {
    const { transport, calls } = recorder([{ status: 200, text: JSON.stringify([{ id: 'a', label: 'A' }]) }]);
    const api = new ApiClient({ apiUrl: 'https://x', clientToken: 'T', transport });
    const reasons = await api.getReasons();
    assertEqual(reasons, [{ id: 'a', label: 'A', active: true }], 'parsed');
    assertEqual(calls[0].url, 'https://x/reasons', 'url');
    assertEqual(calls[0].headers['X-Client-Token'], 'T', 'header');
});

test('getRecentEvents builds query string', async () => {
    const { transport, calls } = recorder([{ status: 200, text: '[]' }]);
    const api = new ApiClient({ apiUrl: 'https://x', clientToken: 'T', transport });
    await api.getRecentEvents('host1', 7);
    assertEqual(calls[0].url, 'https://x/events/recent?host=host1&days=7&limit=100', 'query');
});

test('postEvent throws on non-2xx', async () => {
    const { transport } = recorder([{ status: 503, text: 'down' }]);
    const api = new ApiClient({ apiUrl: 'https://x', clientToken: 'T', transport });
    let threw = false;
    try { await api.postEvent({ event_type: 'login', host: 'h', os_user: 'u', reason: 'r', timestamp: 't' }); }
    catch { threw = true; }
    assertEqual(threw, true, 'threw');
});
