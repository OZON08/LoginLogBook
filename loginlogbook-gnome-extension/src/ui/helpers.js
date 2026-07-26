export function filterReasons(reasons, query) {
    const q = (query || '').trim().toLowerCase();
    if (!q) return reasons.filter(r => r.active !== false);
    return reasons.filter(r => r.active !== false && r.label.toLowerCase().includes(q));
}
export function withinDays(events, days, nowMs) {
    const cutoff = nowMs - days * 86400000;
    return events.filter(e => Date.parse(e.timestamp) >= cutoff);
}
export function reasonFromFreeText(text) {
    const label = (text || '').trim();
    return label ? { id: '', label, active: true } : null;
}
