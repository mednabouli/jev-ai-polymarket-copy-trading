#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WAIT_SECONDS=0
if [[ "${1:-}" == "--wait" ]]; then
  WAIT_SECONDS="${2:-60}"
fi

SERVICES=(postgres mcp-polymarket mcp-telegram jev-ai)
START="$(date +%s)"

log() { printf '\033[1;36m[health]\033[0m %s\n' "$*"; }
ok() { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }
bad() { printf '\033[1;31m[fail]\033[0m %s\n' "$*"; }

while true; do
  FAILED=0
  for service in "${SERVICES[@]}"; do
    status="$(docker compose ps --format json "$service" 2>/dev/null | head -n 1 || true)"
    if [[ -z "$status" ]]; then
      bad "$service: not running"
      FAILED=1
    elif echo "$status" | grep -q 'running'; then
      ok "$service: running"
    else
      bad "$service: unhealthy or exited"
      FAILED=1
    fi
  done

  if [[ "$FAILED" -eq 0 ]]; then
    if docker compose exec -T postgres pg_isready -U postgres -d polymarket >/dev/null 2>&1; then
      ok "postgres: accepting connections"
      exit 0
    fi
    bad "postgres: not accepting connections"
  fi

  NOW="$(date +%s)"
  if (( NOW - START >= WAIT_SECONDS )); then
    log "Container state:"
    docker compose ps
    exit 1
  fi

  log "Retrying in 5 seconds..."
  sleep 5
done
