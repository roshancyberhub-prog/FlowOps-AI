# Implementation status

Status reflects verified behavior only. Follow CHATGPT.md in milestone order.

- [x] Milestone 0: read supplied requirements; confirm empty private repository and available runtimes.
- [x] Milestone 1: FastAPI, PostgreSQL migrations, maintained authentication, organizations, lead CRUD, Next.js, CI, Docker; verify persistence and tenant isolation.
- [x] Milestone 2: validated graph registry, drafts, immutable versions, templates, React Flow editor.
- [ ] Milestone 3: Celery/Redis, durable dispatch, persisted steps, retries, cancellation, approval checkpoints.
- [ ] Milestone 4: bounded CSV imports, reproducible ICP scoring, structured AI adapters, approval inbox, explicit mock email.
- [ ] Milestone 5: real integration, signed and deduplicated inbound webhooks, outbound attempts and retries.
- [ ] Milestone 6: end-to-end verification, hardening, deployment, monitoring, recovery documentation, recorded demo.

## Verified checkpoints

| Milestone | Evidence |
|---|---|
| Foundation | Run 40664524685: PostgreSQL/Redis, migrations and two browser journeys |
| Workflow design | Run 40673713422: 36 backend tests and three browser journeys |
| Execution backend and interface | Run 40734064326: 50 backend tests, migrations, Docker worker/scheduler and four browser journeys |

The execution checkpoint starts a real background run, records its steps, reloads persisted history, pauses at a generic human checkpoint and submits an authorized approval. Screenshot review found the final approval-resume assertion could match a completed step while the overall run was still queued. The assertion now checks the overall run status plus all three completed steps; that strengthened check and the automatic-trigger additions await the next successful CI run.

## Implemented execution behavior

- Durable execution/outbox transaction; organization-scoped idempotency and immutable version pinning.
- Celery step tasks, explicit registered handlers, finite timeouts and per-node attempts, exponential backoff with jitter, failure history and dead letters.
- Duplicate/lost-message reconciliation and expired-lease recovery. An interrupted external intent becomes uncertain and cannot be retried blindly.
- Conditions, lead validation, duplicate lookup, status changes, internal notifications, durable delay and result records.
- Test-mode simulation, current membership checks, cancellation, bounded manual retries, hash/revision-bound approvals, rejection and expiry.
- Execution listing/detail/timeline, run dialog with lead search, approval review and authenticated dispatch health.
- Lead-created triggers share the lead transaction; scheduled triggers persist their next due time and coalesce missed intervals. These latest trigger additions are pending CI acceptance.

Scoring, AI generation and email nodes currently fail explicitly as unconfigured. Inbound/outbound webhooks and CSV imports are not implemented. No public deployment or provider delivery is verified.

## Development and publication

The repository was initially empty. All supplied instructions were read before implementation. Python 3.12, Node 24, uv and npm are available. This local execution environment cannot start PostgreSQL under a non-root user, and the local Chromium download failed; actual database/browser verification comes from GitHub Actions. Local checks cover Python unit/API tests with Redis, Ruff, Mypy, TypeScript, ESLint and the production frontend build.

Feature work is saved on `feature/workflows` and `feature/execution`. Automatic approval review rejected advancing the default branch because the workflow work was scoped to a separate branch. `main` retains the verified foundation; merging and a public deployment have not been performed. Continue feature-branch work and request explicit merge approval only after preparing the complete reviewable result.
