# Implementation status

Status reflects verified behavior only. Follow CHATGPT.md in milestone order.

- [x] Milestone 0: read supplied requirements; confirm empty private repository and available runtimes.
- [x] Milestone 1: FastAPI, PostgreSQL migrations, maintained authentication, organizations, lead CRUD, Next.js, CI, Docker; verify persistence and tenant isolation.
- [x] Milestone 2: validated graph registry, drafts, immutable versions, templates, React Flow editor.
- [x] Milestone 3: Celery/Redis, durable dispatch, persisted steps, retries, cancellation, approval checkpoints.
- [ ] Milestone 4: bounded CSV imports, reproducible ICP scoring, structured AI adapters, approval inbox, explicit mock email.
- [ ] Milestone 5: real integration, signed and deduplicated inbound webhooks, outbound attempts and retries.
- [ ] Milestone 6: end-to-end verification, hardening, deployment, monitoring, recovery documentation, recorded demo.

## Verified checkpoints

| Milestone | Evidence |
|---|---|
| Foundation | Run 40664524685: PostgreSQL/Redis, migrations and two browser journeys |
| Workflow design | Run 40673713422: 36 backend tests and three browser journeys |
| Execution engine | Run 40736331765: 54 backend tests, migrations, Docker worker/scheduler and all four browser journeys |

The execution acceptance run verifies an actual Celery worker completes a background run, persists its steps across reload, pauses at a generic human checkpoint and fully completes after authorized approval. The strengthened browser assertion checks the overall run plus every completed step. Screenshot review confirms the completed desktop/mobile states. PostgreSQL tests cover concurrent duplicate delivery, bounded retries, stale external intents, broker recovery, checkpoint expiry, cancellation after interruption, durable delays, lead-created triggers, interval coalescing and pause behavior. All are green.

## Implemented execution behavior

- Durable execution/outbox transaction; organization-scoped idempotency and immutable version pinning.
- Celery step tasks, explicit registered handlers, finite timeouts and per-node attempts, exponential backoff with jitter, failure history and dead letters.
- Duplicate/lost-message reconciliation and expired-lease recovery. An interrupted external intent becomes uncertain and cannot be retried blindly.
- Conditions, lead validation, duplicate lookup, status changes, internal notifications, durable delay and result records.
- Test-mode simulation, current membership checks, cancellation, bounded manual retries, hash/revision-bound approvals, rejection and expiry.
- Execution listing/detail/timeline, run dialog with lead search, approval review and authenticated dispatch health.
- Lead-created triggers share the lead transaction; scheduled triggers persist their next due time and coalesce missed intervals.

AI and email nodes now support explicitly labelled mock providers or fail as disabled; no live provider is connected. Inbound/outbound webhooks are not implemented. No public deployment or provider delivery is verified.

## Milestone 4 checkpoint: CSV and scoring

Run 40741008963 passed 72 backend tests, PostgreSQL migrations/schema checks and all five Docker-backed browser journeys. The scoring journey calculates a lead score with six reasons and saves a new immutable profile version. The CSV journey uploads a mapped file, waits for the separate worker, inspects inserted/invalid/duplicate counts, filters and reloads the report, and verifies mobile geometry and persisted leads. Backend tests cover concurrent import messages, batch rollback/retry and raw-upload expiry.

The baseline ICP is configurable and versioned. Workflow publication pins a profile UUID; editing score inputs clears the current result. Imports are bounded to 512 KiB and 2000 records and run in transactional batches of 100. Existing and in-file duplicates are skipped, mapped row reports persist, and raw sources are cleared on completion/failure or after seven days. See SCORING.md and IMPORTS.md.

Structured qualification/drafts, approval editing and protected mock email delivery passed backend checkpoint 40744449923 (79 tests). The full outreach interface and expanded CSV-to-reviewed-delivery browser journey are awaiting CI acceptance. The source instructions explicitly authorize a safe mock if credentials are unavailable; no OpenAI key was found. Live AI calls, real email and production deployment are not configured or claimed.

## Development and publication

The repository was initially empty. All supplied instructions were read before implementation. Python 3.12, Node 24, uv and npm are available. This local execution environment cannot start PostgreSQL under a non-root user, and the local Chromium download failed; actual database/browser verification comes from GitHub Actions. Local checks cover Python unit/API tests with Redis, Ruff, Mypy, TypeScript, ESLint and the production frontend build.

Feature work is saved on `feature/workflows`, `feature/execution` and `feature/lead-operations`. Automatic approval review rejected advancing the default branch because the workflow work was scoped to a separate branch. `main` retains the verified foundation; merging and a public deployment have not been performed. Continue feature-branch work and request explicit merge approval only after preparing the complete reviewable result.
