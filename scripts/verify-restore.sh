#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ ${RESTORE_DRILL:-} != 1 ]]; then
  printf '%s\n' 'Set RESTORE_DRILL=1 to create and remove a separate disposable restore database.' >&2
  exit 2
fi
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
backup_dir=$(mktemp -d)
restore_db="flowops_restore_$(date +%s)_${RANDOM}"
cleanup() {
  docker compose exec -T postgres sh -c 'dropdb --if-exists -U "$POSTGRES_USER" "$1"' sh "$restore_db" >/dev/null || true
  rm -f -- "$backup_dir/drill.dump"
  rmdir -- "$backup_dir" || true
}
trap cleanup EXIT
# CI is quiescent after browser tests; compare a stable business-state snapshot.
query='SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM leads), (SELECT count(*) FROM workflow_executions), (SELECT count(*) FROM email_deliveries), (SELECT count(*) FROM webhook_events), (SELECT version_num FROM alembic_version);'
source_counts=$(docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"' sh "$query")
bash scripts/backup.sh "$backup_dir/drill.dump"
docker compose exec -T postgres sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "$restore_db"
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$1" --no-owner --no-acl --single-transaction' sh "$restore_db" < "$backup_dir/drill.dump"
restored_counts=$(docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$1" -Atc "$2"' sh "$restore_db" "$query")
if [[ "$source_counts" != "$restored_counts" ]]; then
  printf '%s\n' 'Restore verification failed: business counts or migration revision differ.' >&2
  exit 1
fi
printf '%s\n' 'Restore verified: users, leads, executions, email receipts, webhook events and migration revision match.'
