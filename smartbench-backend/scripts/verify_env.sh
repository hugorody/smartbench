#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "[verify_env] Docker Compose not found. Install Docker Compose plugin or docker-compose." >&2
    return 1
  fi
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[verify_env] Missing command: $cmd" >&2
    exit 1
  fi
}

wait_for_health() {
  local service="$1"
  local timeout_seconds="${2:-120}"
  local elapsed=0
  local container_id

  container_id="$(compose ps -q "$service")"
  if [[ -z "$container_id" ]]; then
    echo "[verify_env] Service '$service' has no running container ID." >&2
    exit 1
  fi

  while (( elapsed < timeout_seconds )); do
    local status
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)"
    if [[ "$status" == "healthy" || "$status" == "running" ]]; then
      echo "[verify_env] Service '$service' is $status."
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo "[verify_env] Service '$service' did not become healthy/running within ${timeout_seconds}s." >&2
  exit 1
}

if [[ ! -f .env ]]; then
  echo "[verify_env] Missing .env file. Run: cp .env.example .env" >&2
  exit 1
fi

require_command docker
require_command curl

if ! docker info >/dev/null 2>&1; then
  echo "[verify_env] Docker daemon is not reachable. Start Docker first." >&2
  exit 1
fi

read_env_var() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    echo ""
    return
  fi
  echo "${line#*=}"
}

required_vars=(SECRET_KEY DATABASE_URL REDIS_URL POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD)
for var in "${required_vars[@]}"; do
  value="$(read_env_var "$var")"
  if [[ -z "$value" ]]; then
    echo "[verify_env] Required variable '$var' is empty in .env." >&2
    exit 1
  fi
done

for svc in postgres redis web; do
  if ! compose ps --status running --services | grep -qx "$svc"; then
    echo "[verify_env] Service '$svc' is not running. Run: docker compose up -d --build" >&2
    exit 1
  fi
done

wait_for_health postgres 120
wait_for_health redis 120
wait_for_health web 180

echo "[verify_env] Environment verification passed."
