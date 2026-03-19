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

./scripts/verify_env.sh

echo "[db_upgrade] Running database migrations..."
compose exec -T web flask --app app:create_app db upgrade

echo "[db_upgrade] Database upgrade completed."
