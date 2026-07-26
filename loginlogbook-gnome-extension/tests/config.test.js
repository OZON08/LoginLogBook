import { test, assertEqual } from './harness.js';
import { parseEnv, loadConfig, isUsable } from '../src/config.js';

test('parseEnv strips comments, quotes, whitespace', () => {
    const out = parseEnv([
        '# comment',
        'API_URL=https://llb.example.com',
        'CLIENT_TOKEN="secret token"',
        "REASONS_FILE='/x/y'",
        '',
        '  IGNORED_NO_EQUALS  ',
    ].join('\n'));
    assertEqual(out.API_URL, 'https://llb.example.com', 'API_URL');
    assertEqual(out.CLIENT_TOKEN, 'secret token', 'CLIENT_TOKEN');
    assertEqual(out.REASONS_FILE, '/x/y', 'quoted single');
    assertEqual('IGNORED_NO_EQUALS' in out, false, 'no-equals ignored');
});

test('loadConfig applies defaults when file missing', () => {
    const cfg = loadConfig('/nonexistent/loginlogbook.env', '/home/u');
    assertEqual(cfg.apiUrl, '', 'apiUrl empty');
    assertEqual(cfg.caBundle, null, 'caBundle null');
    assertEqual(cfg.cacheDir, '/home/u/.loginlogbook/cache', 'cacheDir default');
    assertEqual(cfg.queueFile, '/home/u/.loginlogbook/queue.json', 'queueFile default');
    assertEqual(isUsable(cfg), false, 'unusable without apiUrl');
});
