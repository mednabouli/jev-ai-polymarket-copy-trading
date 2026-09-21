#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() { printf '\033[1;36m[jev-ai]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "Docker is required: https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."

if [[ ! -f .env ]]; then
  [[ -f env.env ]] || fail "env.env template is missing."
  cp env.env .env
  chmod 600 .env
  warn "Created .env from env.env. Add valid Telegram values before starting services."
else
  log "Using existing .env file."
fi

mkdir -p jev-ai/logs jev-ai/config backups

if grep -qE 'your_claude_code_session_token_here|1234567890:ABCdefGHIjklMNOpqrsTUVwxyz|your_telegram_chat_id_here' .env; then
  warn "Placeholder credentials remain in .env; the Telegram service will not function until replaced."
fi

log "Building images..."
docker compose build

log "Starting core services..."
docker compose up -d postgres mcp-polymarket mcp-telegram jev-ai

log "Waiting for PostgreSQL health check..."
for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres -d polymarket >/dev/null 2>&1; then
    log "PostgreSQL is healthy."
    break
  fi
  sleep 2
done

docker compose ps
log "Setup complete. Run ./scripts/healthcheck.sh to verify all services."
