# Operations

## Startup and readiness

Run `docker compose ps` and `docker compose logs api migrate postgres redis web worker scheduler`. Migrations must finish successfully before the API starts. `/api/v1/health/live` checks the process; `/api/v1/health/ready` checks PostgreSQL and Redis without revealing their error details.

If readiness fails, verify DATABASE_URL/REDIS_URL, database credentials, and private service networking. If Redis is unavailable, rate-limited APIs return 503 rather than dropping request protection. Restart the unavailable dependency and recheck readiness.

## Sign-in or permission failure

A session expires after one hour. Sign in again for 401. Verify the selected workspace and membership for 403. Owners/admins can inspect membership in Team & workspace; only the owner can grant admin. A record from a different workspace returns 404. Check the request ID in an error against the audit trail; never paste passwords or session cookies into logs or issues.

For 429, wait for the Retry-After window. Do not disable limiting to resolve repeated login failures. All users behind the same observed proxy address can share a rate bucket; a public ingress needs a deliberate trusted-client-address policy.

## Leads and duplicates

The normalized email must be unique per workspace, including archived records. Search the archived list and restore the existing record instead of creating a conflicting duplicate. Validation errors appear before database writes. Audit events and lead mutations commit in one transaction.

## Database backup and recovery

The named `postgres_data` Docker volume persists across `docker compose down`. This is persistence, not a backup. Before real data use, configure encrypted `pg_dump` backups, off-host retention and a tested restore into a separate database. Backup/restore automation and recovery-time objectives have not been verified for this project. Do not use `docker compose down --volumes` on data you need to preserve.


## Queued or interrupted execution

Check **Executions → Worker dispatch**, `/api/v1/execution-health` with a signed-in organization session, and `docker compose logs worker scheduler`. Dispatch maintenance runs every three seconds. A stale heartbeat can indicate a stopped worker, scheduler or broker. Restore that service; do not delete PostgreSQL outbox rows. Overdue published messages are reconciled after 60 seconds, with a running task's 180-second lease respected.

MAX_STEP_ATTEMPTS defaults to 3 (range 1–5), EXECUTION_MAX_ACTIVE_SECONDS to 600 (30–3600), and APPROVAL_TTL_HOURS to 72 (1–168). Keep these consistent across API and workers. Retries are limited to the configured attempts per node, with exponential backoff and jitter. Manual retries are limited to five and only offered for eligible failures. Generic configuration/validation failures require a corrected workflow and a new run. An uncertain external result requires provider reconciliation; there is no force-resend button. Cancellation is cooperative and preserves completed actions.

Approval requests expire after 72 hours by default. Pending approval expiry cancels its waiting execution; a new request requires a new run. Decisions use current payload hashes and revisions. A stale decision must be reloaded and reviewed. Permissions are rechecked at each node, so removing a publisher's role can stop their automatic runs.

Pause a workflow to stop new lead-created and scheduled triggers. Existing runs continue unless individually cancelled. After scheduler downtime, interval workflows create one coalesced run, then schedule the next interval from recovery time. Workflows requiring a lead fail with an explicit input error if a scheduled run has no lead; design the scheduled graph accordingly.

Database state is durable; Redis broker messages may be duplicated or lost. Outbox recovery and leases handle those transport conditions. Keep exactly one Beat scheduler per environment. Scale Celery workers independently. Production queue durability, external monitoring and backup/restore drills remain release work.
