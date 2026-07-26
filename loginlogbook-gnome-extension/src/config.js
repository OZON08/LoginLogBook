import GLib from 'gi://GLib';

export function parseEnv(text) {
    const out = {};
    for (let line of text.split('\n')) {
        line = line.trim();
        if (!line || line.startsWith('#')) continue;
        const eq = line.indexOf('=');
        if (eq === -1) continue;
        const key = line.slice(0, eq).trim();
        let val = line.slice(eq + 1).trim();
        if ((val.startsWith('"') && val.endsWith('"')) ||
            (val.startsWith("'") && val.endsWith("'")))
            val = val.slice(1, -1);
        out[key] = val;
    }
    return out;
}

export function loadConfig(path = '/etc/loginlogbook.env', home = GLib.get_home_dir()) {
    let env = {};
    try {
        const [ok, bytes] = GLib.file_get_contents(path);
        if (ok) env = parseEnv(new TextDecoder().decode(bytes));
    } catch {
        // fail-open: missing/unreadable env yields defaults
    }
    return {
        apiUrl: (env.API_URL || '').replace(/\/+$/, ''),
        clientToken: env.CLIENT_TOKEN || '',
        caBundle: env.API_CA_BUNDLE || null,
        cacheDir: env.CACHE_DIR || GLib.build_filenamev([home, '.loginlogbook', 'cache']),
        queueFile: env.QUEUE_FILE || GLib.build_filenamev([home, '.loginlogbook', 'queue.json']),
    };
}

export function isUsable(cfg) {
    return typeof cfg.apiUrl === 'string' && cfg.apiUrl.length > 0;
}
