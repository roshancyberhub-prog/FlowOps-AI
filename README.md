# FlowOps AI

Workflow automation and AI-assisted lead operations built with Next.js, FastAPI, PostgreSQL, Redis and Celery.

Development follows [CHATGPT.md](CHATGPT.md). See [requirements](docs/REQUIREMENTS.md) and the [implementation checklist](IMPLEMENTATION_STATUS.md) for scope and verified progress.

Implemented features include revocable session authentication, workspaces and membership roles, persistent lead management, duplicate protection, audit history, and a React Flow workflow editor with validation, draft saving and immutable published versions. Celery background runs now persist step history, bounded retries, cancellation and human checkpoints. Bounded CSV imports provide saved row reports, and configurable immutable ICP profiles explain lead scores. A labelled mock qualification/draft/email path supports the approval demo; live AI/email providers remain unconfigured. Signed webhooks, tracked outgoing attempts and a real public GitHub repository integration are implemented. The overview uses scoped database analytics and an accessible chart. No live deployment is available yet.

![Verified API-backed overview](docs/screenshots/analytics-overview.png)

![Verified lead management interface](docs/screenshots/leads-desktop.png)

Desktop and mobile screenshots come from the real Docker-backed browser journey in CI.

![Workflow version inspection](docs/screenshots/workflow-builder.png)

![Verified background execution](docs/screenshots/execution-completed.png)

## Local setup

Install Docker with Compose v2 and Python 3, then run from the repository root:

```bash
python3 scripts/setup-env.py
docker compose up --build --wait
```

Open http://localhost:3000, choose **Create an account**, register with a password of 12–128 characters, and create a workspace. The first member is its owner. Add registered users through **Team & workspace**. Owner/admin can manage members; member can manage leads; viewer can inspect leads. Passwords are hashed by FastAPI Users with Argon2; sessions expire after one hour and logout revokes the database token.

API documentation: http://localhost:8000/docs. Liveness: `/api/v1/health/live`. Readiness: `/api/v1/health/ready`. PostgreSQL persists in the `postgres_data` volume. `docker compose down` keeps that volume. Never use `down --volumes` against data you need.

The migration service applies Alembic migrations before the API starts. Migrations do not run in application request handlers.

## Development without application containers

Requires Python 3.12+, uv 0.13.4, Node 24 and npm 11.9.0. Start PostgreSQL and Redis with Compose, then use separate terminals for API, frontend, worker and scheduler:

```bash
docker compose up -d postgres redis
cd services/api
uv sync --frozen
# Export DATABASE_URL, REDIS_URL and WEB_ORIGIN from your root .env.
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000 --no-proxy-headers --no-access-log
```

```bash
cd apps/web
npm ci --ignore-scripts
npm run dev
```

The worker and scheduler use the same exported backend environment:

```bash
cd services/api
uv run celery -A app.execution.worker:celery_app worker --loglevel=WARNING --concurrency=2
```

```bash
cd services/api
uv run celery -A app.execution.worker:celery_app beat --loglevel=WARNING --schedule=/tmp/flowops-celerybeat
```

Publish a basic workflow, choose **Run workflow**, and start a test run. **Executions** shows its background step history. Lead status changes and internal notifications are simulated in test mode. A `Request approval` node configured with `kind: continue` pauses for an owner/admin decision in **Approvals**. Email-specific approvals require a stored draft. The example environment explicitly enables mock AI and mock email; see [outreach](docs/OUTREACH.md). No real AI call or external email is made.

Only public frontend configuration belongs in the browser. Next.js forwards `/api` to `API_INTERNAL_URL` (default `http://127.0.0.1:8000`). No CORS allowance is needed for this same-origin setup. Set `WEB_ORIGIN` to the browser's exact origin. Use `APP_ENV=production` and HTTPS in production to enable secure cookies. Docker targets `http://api:8000` at build time.

## Quality checks

```bash
cd services/api
uv run ruff check .
uv run ruff format --check .
uv run mypy app
# Use a separate PostgreSQL database named flowops_test and Redis database /15.
APP_ENV=test DATABASE_URL=postgresql+asyncpg://flowops:YOUR_PASSWORD@localhost:5432/flowops_test REDIS_URL=redis://localhost:6379/15 uv run alembic upgrade head
APP_ENV=test DATABASE_URL=postgresql+asyncpg://flowops:YOUR_PASSWORD@localhost:5432/flowops_test REDIS_URL=redis://localhost:6379/15 uv run pytest -q
```

```bash
cd apps/web
npm run lint
npm run typecheck
npm run build
npm audit --omit=dev --audit-level=high
npx playwright install chromium
# For the complete retry/video journey, set DEMO_RETRY_FAILURE=true in root .env,
# then recreate api, worker and scheduler. The fault only affects non-production test runs.
# With the Docker application running on localhost:3000:
E2E_EXTERNAL=1 npm test
```

Do not run tests against production data. Browser tests create fictional accounts, workspaces and leads. CI runs migration upgrade/check/downgrade, backend tests against PostgreSQL/Redis, frontend checks, and the documented Docker/browser journey.

## Current limits

There is no password reset or verification email flow yet. Team access currently requires an existing account. Lead deletion archives the record, and changing its status restores it. Normalized email uniqueness applies within each workspace, including archived leads. Lead details show rule-based scores and their reasons; see [scoring](docs/SCORING.md) and [imports](docs/IMPORTS.md).

HTTP bodies are limited to 1 MiB. Redis backs fixed-window limits of 10 authentication requests per 15 minutes and 300 other API requests per minute per observed client address. A reverse proxy can group clients under one address; configure a trusted ingress and a deliberate client-address policy before a public launch. Do not trust arbitrary forwarded-IP headers. Login, passwords and session tokens are never stored in browser JavaScript storage.

See [implementation status](IMPLEMENTATION_STATUS.md) for verified and unverified work.

Integration setup, signature protocol, receiver idempotency contract and delivery recovery: [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

## Release and operations

The production profile, account bootstrap, HTTPS proxy policy, controlled migrations, backup/restore and rollback are documented in [DEPLOYMENT.md](docs/DEPLOYMENT.md). It runs persistent workers on an appropriate Docker host. Use a separate generated production environment; do not reuse development secrets. No public deployment has been performed.

[Monitoring](docs/OBSERVABILITY.md), [retention/deletion rules](docs/RETENTION.md), [security](docs/SECURITY.md) and the [recorded demo](docs/DEMO.md) describe the implemented behavior and its limits. No paid service is required for local Docker use.
