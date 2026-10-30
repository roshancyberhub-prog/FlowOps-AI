# Verification

Use the exact commands in README.md. Tests require a dedicated PostgreSQL test database and Redis database /15; fixtures reset only rate-limit keys in that dedicated Redis database. Fictional accounts and workspace records are created for isolation tests.

Backend coverage includes normalization, invalid input, duplicate handling, authentication requirements, workspace isolation, viewer authorization, lead create/read/update/archive, revocation on logout, request-size limits, CSRF origin checks and Redis rate limits. Tests against PostgreSQL are marked `integration`; unmarked API tests still require Redis.

GitHub Actions runs migrations, schema consistency, all backend tests, linting and type checks. The web job installs dependencies with lifecycle scripts disabled, runs lint/type/audit checks, starts the documented Docker stack, and tests browser registration, workspace creation, persistence after reload, editing, duplicate reports, archive/restore, workspace switching and logout. Browser artifacts include desktop/mobile screenshots and failure traces.

Local checks do not substitute for CI: this execution environment cannot run PostgreSQL under a non-root user, and the Chromium download failed. Record CI results only after inspecting the corresponding run. Foundation Docker/browser checks passed in GitHub Actions run 40664524685.


Workflow acceptance passed run 40673713422: 36 backend tests and three browser journeys. The workflow test exercises disconnected-node validation, node settings, save/publish and immutable version inspection. Pure graph/validation tests do not need Redis; only API tests explicitly reset their dedicated rate-limit keys.


Execution acceptance passed [run 40736331765](https://github.com/roshancyberhub-prog/FlowOps-AI/actions/runs/40736331765): **54 backend tests and all four browser journeys**. The Docker stack includes separate API, Celery worker and Beat scheduler processes. Browser assertions verify overall run completion, persisted steps after reload, approval pause/resume and a 390px document width. Reviewed screenshots are committed under `docs/screenshots/`.

Backend execution tests inject failures at the handler/broker boundary to verify retries without contacting providers. They check three-attempt exhaustion, bounded manual retry acceptance, concurrent duplicate messages, uncertain external-intent recovery, pending approval expiry, cancellation after interruption, transactional outbox retention, automatic lead creation and coalesced scheduled intervals. A durable-delay test verifies that duplicate delivery cannot skip a future due time.


CSV/scoring checkpoint: run 40741008963 passed 72 backend tests and five browser journeys, including actual background CSV import, record filtering/reload/mobile width, scored lead reasons and profile-version creation.


Milestone 4 acceptance: [run 40747693463](https://github.com/roshancyberhub-prog/FlowOps-AI/actions/runs/40747693463) passed **82 backend tests and all five browser journeys**. The expanded import journey publishes outreach, processes fitting/invalid/duplicate records through separate workers, edits a draft, verifies stale review rejection, approves one current revision, rejects the other and checks all nine successful steps plus exactly one mock receipt. No external email is sent. Backend additions cover current approver authorization and lead facts at send time. Screenshots were visually reviewed for desktop/mobile layout, complete score reasons, edited draft content and simulated receipts.

## Release readiness checkpoint

[Run 41030254236](https://github.com/roshancyberhub-prog/FlowOps-AI/actions/runs/41030254236) passed 116 backend tests and all five Docker-backed browser journeys. Python runtime and npm dependency audits found no known vulnerabilities. Caddy accepted the production configuration. A real custom-format PostgreSQL dump restored into a separate database; users/leads/executions/email receipts/webhook events and Alembic revision matched.

The recorded journey additionally enables the explicit non-production `DEMO_RETRY_FAILURE` fault, verifies failed then successful mock-draft attempts, registers a separate viewer, adds that user through Team, checks backend approval denial (403), cross-workspace execution denial (404), and shows read-only approval controls. The fault cannot affect production or live mode; automated gate tests cover both. Native review mutated signature verification and observed a failing security test, then restored the implementation and reran it successfully.

New setup-isolation/symlink and log-export tests, independent production settings and digest pinning are undergoing the final release run. Native setup/metrics checks, Ruff, Mypy, ESLint, TypeScript and representative unit tests pass. The native vulnerability-service request timed out under the workspace proxy; the actual successful vulnerability audit evidence is from CI. No public-host smoke/performance/alert test is claimed.
