#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(mktemp -d)"
DESTDIR="$root" "$here/install.sh"
ext="$root/usr/share/gnome-shell/extensions/loginlogbook@ozon08.github.io"
test -f "$ext/metadata.json" || { echo "FAIL: metadata not installed"; exit 1; }
test -f "$ext/extension.js" || { echo "FAIL: extension.js not installed"; exit 1; }
grep -q "loginlogbook@ozon08.github.io" "$root/etc/dconf/db/local.d/00-loginlogbook" || { echo "FAIL: dconf default missing"; exit 1; }
grep -q "enabled-extensions" "$root/etc/dconf/db/local.d/locks/loginlogbook" || { echo "FAIL: dconf lock missing"; exit 1; }
echo "PASS"
