# Verification

Use the exact commands in README.md. Tests require a dedicated PostgreSQL test database and Redis database /15; fixtures reset only rate-limit keys in that dedicated Redis database. Fictional accounts and workspace records are created for isolation tests.

Backend coverage includes normalization, invalid input, duplicate handling, authentication requirements, workspace isolation, viewer authorization, lead create/read/update/archive, revocation on logout, request-size limits, CSRF origin checks and Redis rate limits. Tests against PostgreSQL are marked `integration`; unmarked API tests still require Redis.

GitHub Actions runs migrations, schema consistency, all backend tests, linting and type checks. The web job installs dependencies with lifecycle scripts disabled, runs lint/type/audit checks, starts the documented Docker stack, and tests browser registration, workspace creation, persistence after reload, editing, duplicate reports, archive/restore, workspace switching and logout. Browser artifacts include desktop/mobile screenshots and failure traces.

Local checks do not substitute for CI: this execution environment cannot run PostgreSQL under a non-root user, and the Chromium download failed. Record CI results only after inspecting the corresponding run. Foundation Docker/browser checks passed in GitHub Actions run 40664524685.
