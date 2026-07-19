#!/bin/sh
# certbot deploy-hook: copy the freshly issued/renewed cert into the single
# path nginx reads. Runs INSIDE the certbot container. certbot sets
# RENEWED_LINEAGE to /etc/letsencrypt/live/<domain> for deploy hooks.
set -eu

: "${RENEWED_LINEAGE:?RENEWED_LINEAGE not set — deploy-hook must be run by certbot}"

cp "$RENEWED_LINEAGE/fullchain.pem" /etc/nginx/certs/server.crt
cp "$RENEWED_LINEAGE/privkey.pem"   /etc/nginx/certs/server.key
echo "deploy-hook: copied $RENEWED_LINEAGE -> /etc/nginx/certs/server.{crt,key}"
