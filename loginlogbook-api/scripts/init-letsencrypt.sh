#!/bin/sh
# One-time Let's Encrypt issuance for LoginLogBook.
#
# Prereqs:
#   - stack is up (nginx serving on :80/:443 with the self-signed bootstrap cert)
#   - TLS_DOMAIN and CERTBOT_EMAIL are set in .env
#   - DNS for TLS_DOMAIN points at this host, ports 80/443 reachable
#
# Usage: ./scripts/init-letsencrypt.sh [--staging]
set -eu

cd "$(dirname "$0")/.."

if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

: "${TLS_DOMAIN:?TLS_DOMAIN not set in .env}"
: "${CERTBOT_EMAIL:?CERTBOT_EMAIL not set in .env}"

STAGING=""
if [ "${1:-}" = "--staging" ]; then
    STAGING="--staging"
    echo "init-letsencrypt: using Let's Encrypt STAGING environment"
fi

echo "init-letsencrypt: requesting certificate for $TLS_DOMAIN"
docker compose --profile certbot run --rm --entrypoint certbot certbot \
    certonly --webroot -w /var/www/certbot \
    -d "$TLS_DOMAIN" \
    --email "$CERTBOT_EMAIL" \
    --agree-tos --no-eff-email $STAGING \
    --deploy-hook /scripts/deploy-hook.sh

echo "init-letsencrypt: reloading nginx to pick up the new certificate"
docker compose exec nginx nginx -s reload

echo "init-letsencrypt: done. https://$TLS_DOMAIN should now serve a trusted cert."
