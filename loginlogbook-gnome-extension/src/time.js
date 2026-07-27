import GLib from 'gi://GLib';

// RFC3339 timestamp accepted by the API's pydantic datetime parser.
// GLib.DateTime.format_iso8601() emits an abbreviated, colon-less UTC offset
// ("...+02") that pydantic rejects with 422; the "%:z" specifier produces the
// required "+02:00" form.
export function rfc3339(dt) {
    return dt.format('%Y-%m-%dT%H:%M:%S%:z');
}

export function nowRfc3339() {
    return rfc3339(GLib.DateTime.new_now_local());
}
