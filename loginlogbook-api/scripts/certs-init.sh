#!/bin/sh
# Bootstrap TLS cert: generate a self-signed pair only if none exists.
# Runs as a one-shot container before nginx starts. Never overwrites an
# existing cert (including one written by certbot).
set -eu

CRT=/etc/nginx/certs/server.crt
KEY=/etc/nginx/certs/server.key

if [ -f "$CRT" ] && [ -f "$KEY" ]; then
    echo "certs-init: $CRT and $KEY already exist — leaving them untouched."
    exit 0
fi

echo "certs-init: generating self-signed certificate for CN=${TLS_DOMAIN:-loginlogbook.local}"
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
    -keyout "$KEY" -out "$CRT" \
    -subj "/CN=${TLS_DOMAIN:-loginlogbook.local}"
echo "certs-init: done."
