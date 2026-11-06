#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ENV_FILE=${1:-$ROOT_DIR/.env.production}
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.production.yml")

"$ROOT_DIR/ops/production/preflight.sh" "$ENV_FILE"
"$ROOT_DIR/ops/production/backup.sh" "$ENV_FILE"
"${COMPOSE[@]}" pull app db minio
"${COMPOSE[@]}" up -d db minio
"${COMPOSE[@]}" run --rm --no-deps app alembic upgrade head
"${COMPOSE[@]}" up -d --no-deps app
"${COMPOSE[@]}" ps

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
curl --fail --silent --show-error --retry 12 --retry-delay 5 \
  "http://${APP_BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-8080}/ready" >/dev/null
printf 'Deploy smoke test passed. Record release and image digest in the change ticket.\n'
