#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ENV_FILE=${1:-$ROOT_DIR/.env.production}
OUTPUT_DIR=${BACKUP_OUTPUT_DIR:-$ROOT_DIR/ops/production/backup-output}
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.production.yml")
command -v age >/dev/null || { echo 'age is required for encrypted backups' >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
[[ -f "${BACKUP_AGE_RECIPIENTS_FILE:?Set BACKUP_AGE_RECIPIENTS_FILE}" ]] || exit 1
mkdir -p "$OUTPUT_DIR"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/minio"

"${COMPOSE[@]}" exec -T db pg_dump --format=custom --no-owner --no-acl \
  --username=missioni --dbname=missioni >"$stage/postgres.dump"
"${COMPOSE[@]}" run --rm --no-deps -v "$stage/minio:/transfer" minio-tool
git -C "$ROOT_DIR" rev-parse HEAD >"$stage/git-commit"
"${COMPOSE[@]}" images --format json >"$stage/images.json"
(cd "$stage" && find postgres.dump minio -type f -print0 | sort -z | xargs -0 shasum -a 256 >SHA256SUMS)

stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$OUTPUT_DIR/missioni-dist-$stamp.tar.age"
tar -C "$stage" -cf - . | age -R "$BACKUP_AGE_RECIPIENTS_FILE" -o "$archive"
test -s "$archive"
printf 'Encrypted backup created: %s\n' "$archive"
