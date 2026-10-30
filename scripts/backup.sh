#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ $# != 1 || -e $1 || -L $1 ]]; then
  printf '%s\n' 'Usage: bash scripts/backup.sh NEW_PRIVATE_BACKUP_FILE' >&2
  exit 2
fi
# Refuse replacement and symlinks, including a race after the initial check.
set -o noclobber
if ! docker compose exec -T postgres sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl' > "$1"; then
  printf '%s\n' 'Backup failed. Treat any partial output as invalid.' >&2
  exit 1
fi
printf '%s\n' 'Database backup completed. Encrypt and copy it off this host before retention.'
