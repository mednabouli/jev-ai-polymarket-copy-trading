#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENVIRONMENT="${ENVIRONMENT:-production}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"

log() { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "Docker is required."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."
[[ -f .env ]] || fail "Missing .env. Run ./scripts/setup.sh first."

if grep -qE 'your_claude_code_session_token_here|1234567890:ABCdefGHIjklMNOpqrsTUVwxyz|your_telegram_chat_id_here' .env; then
  fail "Refusing deployment: replace placeholder values in .env."
fi

export ENVIRONMENT IMAGE_TAG
log "Deploying environment=$ENVIRONMENT image_tag=$IMAGE_TAG"

./scripts/backup.sh --quiet || log "No database backup created (database may not be running yet)."
docker compose pull
docker compose build --pull
docker compose up -d --remove-orphans

./scripts/healthcheck.sh --wait 60
log "Deployment completed successfully."
