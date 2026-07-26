#!/usr/bin/env bash
# Install the LoginLogBook GNOME extension system-wide and force-enable it via
# dconf. Set DESTDIR for a staged/dry-run install (skips `dconf update`).
set -euo pipefail
UUID="loginlogbook@ozon08.github.io"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DESTDIR="${DESTDIR:-}"

extdir="${DESTDIR}/usr/share/gnome-shell/extensions/${UUID}"
mkdir -p "$extdir"
cp -r "$SRC/metadata.json" "$SRC/extension.js" "$SRC/src" "$SRC/locales" "$extdir/"

dconfdir="${DESTDIR}/etc/dconf/db/local.d"
mkdir -p "$dconfdir/locks"
cat > "$dconfdir/00-loginlogbook" <<EOF
[org/gnome/shell]
enabled-extensions=['${UUID}']
EOF
cat > "$dconfdir/locks/loginlogbook" <<EOF
/org/gnome/shell/enabled-extensions
EOF

if [ -z "$DESTDIR" ]; then
    dconf update
    echo "Installed and enforced ${UUID}. Users must re-login to apply."
else
    echo "Staged install under ${DESTDIR} (dconf update skipped)."
fi
