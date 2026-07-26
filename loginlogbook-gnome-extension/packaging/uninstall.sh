#!/usr/bin/env bash
set -euo pipefail
UUID="loginlogbook@ozon08.github.io"
DESTDIR="${DESTDIR:-}"
rm -rf "${DESTDIR}/usr/share/gnome-shell/extensions/${UUID}"
rm -f "${DESTDIR}/etc/dconf/db/local.d/00-loginlogbook"
rm -f "${DESTDIR}/etc/dconf/db/local.d/locks/loginlogbook"
if [ -z "$DESTDIR" ]; then dconf update; fi
echo "Removed ${UUID}."
