#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ENV_FILE=${1:-$ROOT_DIR/.env.production}

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command -v docker >/dev/null || fail "docker is required"
docker compose version >/dev/null || fail "Docker Compose v2 is required"
[[ -f "$ENV_FILE" ]] || fail "missing production env file: $ENV_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

for name in APP_IMAGE ALLOWED_HOSTS ALLOWED_ORIGINS FORWARDED_ALLOW_IPS \
  DATABASE_URL_SECRET_FILE POSTGRES_PASSWORD_SECRET_FILE \
  MINIO_ACCESS_KEY_SECRET_FILE MINIO_SECRET_KEY_SECRET_FILE; do
  value=${!name:-}
  [[ -n "$value" ]] || fail "$name is required"
  [[ "$value" != *CHANGE_ME* ]] || fail "$name still contains CHANGE_ME"
done
[[ "$ALLOWED_ORIGINS" == https://* ]] || fail "ALLOWED_ORIGINS must use institutional HTTPS"
[[ "$FORWARDED_ALLOW_IPS" != "*" ]] || fail "FORWARDED_ALLOW_IPS cannot trust every client"
[[ "$APP_BIND_ADDRESS" == "127.0.0.1" || "$APP_BIND_ADDRESS" == "::1" ]] || \
  printf 'WARNING: non-loopback bind requires ICT firewall allowlisting\n' >&2

for path in "$DATABASE_URL_SECRET_FILE" "$POSTGRES_PASSWORD_SECRET_FILE" \
  "$MINIO_ACCESS_KEY_SECRET_FILE" "$MINIO_SECRET_KEY_SECRET_FILE"; do
  [[ -f "$path" && -s "$path" ]] || fail "secret file missing or empty: $path"
  mode=$(stat -f '%Lp' "$path" 2>/dev/null || stat -c '%a' "$path")
  [[ "$mode" == "600" || "$mode" == "400" ]] || fail "secret file must be mode 0600/0400: $path"
done

docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.production.yml" config --quiet
python3 "$ROOT_DIR/scripts/check_public_repo.py"
printf 'Preflight passed; no deployment was performed.\n'
