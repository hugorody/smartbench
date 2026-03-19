#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

echo "[reset_local_stack] Stopping and removing local stack (including volumes)..."
compose down --volumes --remove-orphans

echo "[reset_local_stack] Local stack reset complete."
