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

echo "[db_seed] Seeding demo data..."
compose exec -T web python -m scripts.seed_demo

echo "[db_seed] Seed completed."
