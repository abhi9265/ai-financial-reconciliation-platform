#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_FILE:?BACKUP_FILE must point to a pg_dump custom-format backup}"

test -f "$BACKUP_FILE"

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Set CONFIRM_RESTORE=YES to perform a destructive restore."
  exit 2
fi

pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$BACKUP_FILE"
echo "Restore completed from $BACKUP_FILE"
