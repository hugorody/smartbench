#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${APP_BASE_URL:-http://localhost:8000}"
COOKIE_FILE="$(mktemp)"
HEADERS_FILE="$(mktemp)"
BODY_FILE="$(mktemp)"
trap 'rm -f "$COOKIE_FILE" "$HEADERS_FILE" "$BODY_FILE"' EXIT

assert_status() {
  local expected="$1"
  local actual="$2"
  local context="$3"
  if [[ "$actual" != "$expected" ]]; then
    echo "[smoke_api] $context failed: expected HTTP $expected, got $actual" >&2
    [[ -s "$BODY_FILE" ]] && cat "$BODY_FILE" >&2
    exit 1
  fi
}

echo "[smoke_api] Checking /health..."
status="$(curl -sS -o "$BODY_FILE" -w "%{http_code}" "$BASE_URL/health")"
assert_status "200" "$status" "GET /health"
if ! grep -q '"status"' "$BODY_FILE"; then
  echo "[smoke_api] /health response body missing status payload." >&2
  cat "$BODY_FILE" >&2
  exit 1
fi

echo "[smoke_api] Checking login page..."
status="$(curl -sS -o "$BODY_FILE" -w "%{http_code}" "$BASE_URL/auth/login")"
assert_status "200" "$status" "GET /auth/login"

echo "[smoke_api] Checking protected route redirect before auth..."
status="$(curl -sS -D "$HEADERS_FILE" -o "$BODY_FILE" -w "%{http_code}" "$BASE_URL/")"
assert_status "302" "$status" "GET / (unauthenticated)"
if ! grep -qi 'location: .*auth/login' "$HEADERS_FILE"; then
  echo "[smoke_api] Expected redirect to /auth/login for unauthenticated access." >&2
  cat "$HEADERS_FILE" >&2
  exit 1
fi

echo "[smoke_api] Logging in through scaffold auth..."
status="$(curl -sS -D "$HEADERS_FILE" -o "$BODY_FILE" -w "%{http_code}" \
  -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
  -X POST "$BASE_URL/auth/login" \
  --data-urlencode "email=homologation@smartbench.local" \
  --data-urlencode "full_name=Homologation User")"
assert_status "302" "$status" "POST /auth/login"

echo "[smoke_api] Checking protected route after auth..."
status="$(curl -sS -o "$BODY_FILE" -w "%{http_code}" -c "$COOKIE_FILE" -b "$COOKIE_FILE" "$BASE_URL/")"
assert_status "200" "$status" "GET / (authenticated)"
if ! grep -qi 'SmartBench' "$BODY_FILE"; then
  echo "[smoke_api] Authenticated dashboard response did not contain expected content." >&2
  cat "$BODY_FILE" >&2
  exit 1
fi

echo "[smoke_api] Smoke validation passed."
