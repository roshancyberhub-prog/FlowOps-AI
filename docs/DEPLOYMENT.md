# Deployment and recovery

No public deployment has been made. CI verifies a disposable Docker installation, production configuration syntax and an isolated PostgreSQL restore. A public hostname, suitable Docker host and approval to merge the release branch are still needed. No paid hosting, DNS change, production credential or real email provider has been provisioned.

## Production profile

The supplied profile runs Next.js, FastAPI, PostgreSQL, Redis, persistent Celery workers, one Beat scheduler and a Caddy HTTPS ingress. It fits an existing Docker machine; hosting costs depend on the chosen host. A serverless frontend deployment alone cannot run the persistent workers. The database and Redis are bound to loopback on the host, with private container networking. The profile is for the labelled portfolio/demo providers; live AI/email need separate configured adapters and credentials.

On an approved host, check out the exact reviewed release commit and run from the repository root:

```bash
python3 scripts/setup-env.py --production-domain YOUR_OWNED_HOSTNAME
FLOWOPS_PRODUCTION=1 bash scripts/compose.sh config --quiet
```

Use an owned hostname, without `https://`, a port or a path. The helper creates `.env.production` with different random database/signing secrets from development and refuses to replace files or symlinks. It is ignored by Git. Keep it private and provision the same backend settings to API, workers and scheduler. Production uses `APP_ENV=production`, an exact HTTPS `WEB_ORIGIN`, Secure cookies, and public registration closed by default. `FLOWOPS_ENV_FILE` selects the correct runtime settings; `scripts/compose.sh` selects the separate `flowops-prod` project and production overlay.

Before starting, point the hostname at the approved host, allow inbound 80/443, and verify the host has enough disk, memory and a working backup destination. Caddy obtains HTTPS certificates; its data volume contains private certificate material. The profile reserves `172.30.80.0/24` and Caddy `172.30.80.10`. If that subnet conflicts, update both the network configuration and Uvicorn's trusted proxy address together before validation.

```bash
FLOWOPS_PRODUCTION=1 bash scripts/compose.sh build
FLOWOPS_PRODUCTION=1 bash scripts/compose.sh up -d postgres redis
FLOWOPS_PRODUCTION=1 bash scripts/compose.sh run --rm migrate
FLOWOPS_PRODUCTION=1 bash scripts/compose.sh up -d --wait api worker scheduler web caddy
curl --fail https://YOUR_OWNED_HOSTNAME/api/v1/health/ready
```

CI is the release gate. Do not deploy a commit whose required checks failed or whose code has not been reviewed. Base container images are pinned to digests observed in successful CI run 41030254236. Python and npm dependencies are locked and audited. Updating an image digest or dependency is a reviewed change, followed by these checks again.

## Account bootstrap and smoke checks

For the first account only, deliberately set `ALLOW_PUBLIC_REGISTRATION=true` in `.env.production`, recreate the API and register through HTTPS. Then set it back to `false` and recreate the API. Registration creates a normal user; each newly created workspace is owned by its creator. Existing accounts can sign in while public registration is closed. There are no default credentials. Additional accounts require an operator-controlled registration window; verification/reset email is not implemented.

Confirm sign-in/logout and the Secure/HttpOnly/SameSite cookie. Create a fictional lead, publish a test workflow, run it through the separate worker, inspect steps, and verify `/api/v1/execution-health` with an authenticated workspace session. Test a signed duplicate webhook and an owner/admin approval, then verify that a viewer cannot approve. Keep exactly one Beat scheduler. Do not use real customer data for the initial portfolio deployment.

Caddy routes browser `/api/*` requests directly to FastAPI and replaces untrusted forwarding headers. Uvicorn accepts forwarding information only from the fixed Caddy address, so the observed client IP is usable for rate limiting. Direct Next.js rewrites remain useful in development. If another CDN/proxy is added, review the entire trust chain rather than accepting arbitrary `X-Forwarded-For` values. Primary references: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy and https://uvicorn.dev/settings/ .

## Backups and restore

The PostgreSQL volume is persistence, not a backup. Proposed operational targets: an encrypted off-host backup every 24 hours, 7 daily and 4 weekly copies, RPO 24 hours and RTO 2 hours. These are targets, not measured production guarantees. Adjust them before real data use. Back up before each schema change and test a restore monthly. Signing keys, `.env.production` and Caddy certificate data require separate encrypted secret backups.

```bash
# A new private filename outside the checkout; the script refuses replacement.
FLOWOPS_PRODUCTION=1 bash scripts/backup.sh /SECURE_BACKUP_DIRECTORY/flowops-YYYYMMDD.dump
# Run while writes are stopped for a consistent count comparison.
FLOWOPS_PRODUCTION=1 RESTORE_DRILL=1 bash scripts/verify-restore.sh
```

The drill creates a uniquely named separate database, restores the full custom-format dump in one transaction, compares users/leads/executions/email receipts/webhook events/migration revision, and removes only the database it created. It never restores over the live database. CI verified this procedure against the browser-generated fictional dataset. Encryption/off-host transfer and production recovery time still depend on the operator's chosen storage and host.

For an incident restore, stop API, worker and scheduler writes, restore to a **new** database, verify the migration revision and business counts, then deliberately change `POSTGRES_DB`/database settings to the restored database. Keep the original database intact for investigation. Before resuming workers, reconcile in-flight external intents with receivers/providers: a restored database may predate a side effect. Keep outbound integrations disabled until reconciliation is complete. Reapply required migrations only after checking compatibility.

## Rollback

Record the prior release SHA, take a backup, and deploy the reviewed SHA. If the new app fails smoke checks, stop API/worker/scheduler, check out and rebuild the previous compatible SHA, then restart and verify health and sign-in. Preserve database state. Do not blindly downgrade a populated database; migrations are reversible in disposable CI, but data compatibility must be reviewed for a real rollback. Disable a problematic integration or pause new workflow triggers while investigating. Completed external effects are not reversed by a rollback.

A public deployment is accepted only after HTTPS, readiness, worker dispatch, sign-in, one complete fictional workflow, permission denial and monitoring are checked on the actual host. This has not yet happened.
