#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD before starting}"
: "${RECONCILIATION_API_KEY:?set RECONCILIATION_API_KEY before starting}"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-reconciliation-production-local}"

echo "Starting zero-cost production-like deployment..."
echo "No cloud resources are created by this script."

docker compose \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  up -d --build

cleanup() {
  echo "Stopping zero-cost production-like deployment..."
  docker compose \
    -f docker-compose.yml \
    -f docker-compose.production.yml \
    down
}
trap cleanup INT TERM

echo "Waiting for readiness..."
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8080/ready >/dev/null 2>&1; then
    echo "Ready: http://localhost:8080"
    echo "Health: http://localhost:8080/health"
    echo "Press Ctrl-C to stop."
    wait
    exit 0
  fi
  sleep 2
done

echo "Readiness check failed."
docker compose -f docker-compose.yml -f docker-compose.production.yml ps
docker compose -f docker-compose.yml -f docker-compose.production.yml logs --tail=80 api edge
exit 1
