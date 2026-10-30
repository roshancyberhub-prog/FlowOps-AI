#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
if [[ ${FLOWOPS_PRODUCTION:-0} == 1 ]]; then
  exec docker compose --env-file .env.production -p flowops-prod -f docker-compose.yml -f deployment/compose.production.yml "$@"
fi
exec docker compose "$@"
