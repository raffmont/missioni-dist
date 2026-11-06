#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ $# -eq 2 ]] || { echo "usage: $0 ENV_FILE ENCRYPTED_BACKUP" >&2; exit 2; }
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ENV_FILE=$1
ARCHIVE=$2
COMPOSE_FILE="$ROOT_DIR/compose.production.yml"
command -v age >/dev/null || { echo 'age is required' >&2; exit 1; }
stage=$(mktemp -d)
project="missioni-restore-test-$(date +%s)"
cleanup() {
  docker compose -p "$project" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
  rm -rf "$stage"
}
trap cleanup EXIT

age --decrypt "$ARCHIVE" | tar -C "$stage" -xf -
(cd "$stage" && shasum -a 256 -c SHA256SUMS)
compose=(docker compose -p "$project" --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
"${compose[@]}" up -d db minio
"${compose[@]}" exec -T db pg_restore --clean --if-exists --no-owner --no-acl \
  --username=missioni --dbname=missioni <"$stage/postgres.dump"
"${compose[@]}" run --rm --no-deps -v "$stage/minio:/transfer:ro" minio-tool \
  'MC_HOST_source="http://$(cat /run/secrets/minio_access_key):$(cat /run/secrets/minio_secret_key)@minio:9000" mc mirror --overwrite /transfer source/missioni-private'
rows=$("${compose[@]}" exec -T db psql -U missioni -d missioni -Atc 'select count(*) from users')
objects=$(find "$stage/minio" -type f | wc -l | tr -d ' ')
printf 'Isolated restore passed: users=%s, restored source objects=%s. Environment will be destroyed.\n' "$rows" "$objects"
