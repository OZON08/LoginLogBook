const HEX = /^#[0-9A-Fa-f]{6}$/;

export function safeLogoBg(hex) {
    return typeof hex === 'string' && HEX.test(hex) ? hex : '#1E293B';
}

export function Reason(o = {}) {
    return { id: o.id, label: o.label, active: o.active === undefined ? true : !!o.active };
}

export function AppConfig(o = {}) {
    return {
        recent_days: o.recent_days === undefined ? 7 : o.recent_days,
        allow_free_text: o.allow_free_text === undefined ? true : !!o.allow_free_text,
    };
}

export function BrandingConfig(o = {}) {
    return {
        logo_height: o.logo_height === undefined ? 120 : o.logo_height,
        logo_bg: o.logo_bg === undefined ? '#1E293B' : o.logo_bg,
    };
}

export function LanguageSetting(o = {}) {
    return { language: o.language || 'de', available: o.available || [] };
}

export function EventIn(o = {}) {
    if (o.event_type !== 'login' && o.event_type !== 'logout')
        throw new Error(`invalid event_type: ${o.event_type}`);
    for (const k of ['host', 'os_user', 'timestamp'])
        if (!o[k]) throw new Error(`missing ${k}`);
    return {
        event_type: o.event_type,
        host: o.host,
        os_user: o.os_user,
        reason: o.reason === undefined ? null : o.reason,
        timestamp: o.timestamp,
    };
}

export function EventOut(o = {}) {
    return {
        event_type: o.event_type,
        host: o.host,
        os_user: o.os_user,
        reason: o.reason === undefined ? null : o.reason,
        timestamp: o.timestamp,
    };
}
