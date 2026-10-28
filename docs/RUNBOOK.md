# Foundation operations

## Startup and readiness

Run `docker compose ps` and `docker compose logs api migrate postgres redis web`. Migrations must finish successfully before the API starts. `/api/v1/health/live` checks the process; `/api/v1/health/ready` checks PostgreSQL and Redis without revealing their error details.

If readiness fails, verify DATABASE_URL/REDIS_URL, database credentials, and private service networking. If Redis is unavailable, rate-limited APIs return 503 rather than dropping request protection. Restart the unavailable dependency and recheck readiness.

## Sign-in or permission failure

A session expires after one hour. Sign in again for 401. Verify the selected workspace and membership for 403. Owners/admins can inspect membership in Team & workspace; only the owner can grant admin. A record from a different workspace returns 404. Check the request ID in an error against the audit trail; never paste passwords or session cookies into logs or issues.

For 429, wait for the Retry-After window. Do not disable limiting to resolve repeated login failures. All users behind the same observed proxy address can share a rate bucket; a public ingress needs a deliberate trusted-client-address policy.

## Leads and duplicates

The normalized email must be unique per workspace, including archived records. Search the archived list and restore the existing record instead of creating a conflicting duplicate. Validation errors appear before database writes. Audit events and lead mutations commit in one transaction.

## Database backup and recovery

The named `postgres_data` Docker volume persists across `docker compose down`. This is persistence, not a backup. Before real data use, configure encrypted `pg_dump` backups, off-host retention and a tested restore into a separate database. Backup/restore automation and recovery-time objectives have not been verified for this project. Do not use `docker compose down --volumes` on data you need to preserve.
