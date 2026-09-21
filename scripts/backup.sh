#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

QUIET=false
[[ "${1:-}" == "--quiet" ]] && QUIET=true

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="$BACKUP_DIR/polymarket_${TIMESTAMP}.sql.gz"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

log() { $QUIET || printf '\033[1;36m[backup]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "Docker is required."
mkdir -p "$BACKUP_DIR"

if ! docker compose ps --status running --services | grep -qx postgres; then
  fail "PostgreSQL container is not running; no backup was created."
fi

log "Creating compressed PostgreSQL backup..."
docker compose exec -T postgres pg_dump -U postgres -d polymarket --no-owner --no-privileges | gzip > "$ARCHIVE"

test -s "$ARCHIVE" || fail "Backup file is empty."
find "$BACKUP_DIR" -type f -name 'polymarket_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete

log "Backup created: $ARCHIVE"
