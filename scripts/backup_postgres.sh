#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_DIR:=./backups}"
mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$BACKUP_DIR/reconciliation-$timestamp.dump"

pg_dump "$DATABASE_URL" --format=custom --file="$output"
sha256sum "$output" > "$output.sha256"

echo "Backup written to $output"
