#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() { printf '\033[1;33m[reset]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "${CONFIRM_RESET:-}" == "YES" ]] || fail "Refusing destructive reset. Run: CONFIRM_RESET=YES ./scripts/reset.sh"
command -v docker >/dev/null 2>&1 || fail "Docker is required."

if docker compose ps --status running --services | grep -qx postgres; then
  log "Creating a backup before reset..."
  ./scripts/backup.sh
fi

log "Stopping services and Removing database volumes..."
docker compose down -v --remove-orphans

log "Starting a clean stack..."
docker compose up -d
./scripts/healthcheck.sh --wait 60
log "Reset complete."
