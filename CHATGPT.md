# FlowOps AI — Project Instructions for ChatGPT and Coding Agents

> Place this file at the root of the `flowops-ai` repository. Treat it as the primary project instruction file. Follow it together with the detailed requirements in `/docs`. If a requirement is unclear, inspect the existing code and documentation first, then choose the smallest safe implementation that fits the architecture.

## 1. Role and mission

Act as a senior full-stack engineer, Python backend engineer, workflow automation architect, database engineer, QA engineer, security engineer, and DevOps engineer.

Build **FlowOps AI**, a production-style full-stack workflow automation and AI-powered lead operations platform. It must be a working application, not a static UI or a collection of mock screens.

The product must demonstrate:
- Full-stack software development.
- Python and FastAPI backend engineering.
- Workflow design and asynchronous execution.
- AI integration with validated structured outputs.
- REST APIs and webhooks.
- PostgreSQL data modeling.
- Reliability, retries, and idempotency.
- Authentication, authorization, and tenant isolation.
- Automated testing, Docker, CI/CD, deployment, and monitoring.

Optimize for maintainability, security, and demonstrable end-to-end functionality. Do not over-engineer the first version.

## 2. Product definition

FlowOps AI lets businesses build workflows, import and qualify leads, connect external services, approve AI-generated communications, execute background jobs, and inspect execution history from a single dashboard.

### Required modules

1. **Workflow builder**
   - Visual workflow editor.
   - Triggers, conditions, actions, and approval steps.
   - Draft and published workflow versions.
   - Graph validation.
   - Templates and test runs.
   - Execution history.

2. **AI-powered lead operations**
   - CSV import with row-level validation reports.
   - Lead CRUD, search, filters, and pagination.
   - Email normalization and duplicate detection.
   - Transparent, deterministic ICP-based lead scoring.
   - AI-assisted qualification and outreach drafting.
   - Human approval before protected external sending.
   - Import history and processing status.

3. **Reliable execution engine**
   - Background execution through Celery and Redis.
   - Persisted execution and step records.
   - Retry policies, timeouts, and exponential backoff with jitter.
   - Idempotency protections.
   - Approval pauses and resumptions.
   - Cancellation where safe.
   - Failure details, retry history, and dead-letter handling.

4. **Integrations and webhooks**
   - Versioned REST API.
   - Incoming and outgoing webhooks.
   - One real external integration selected based on available credentials.
   - AI provider integration.
   - Email provider or SMTP integration.
   - Optional n8n webhook integration.
   - Connection testing, delivery records, signature verification where supported, and safe secret handling.

5. **Production-ready engineering**
   - Authentication and role-based access control.
   - Organization-level tenant isolation.
   - PostgreSQL and migrations.
   - Validation, audit logs, and rate limiting.
   - Automated tests and quality checks.
   - Docker and Docker Compose.
   - GitHub Actions CI/CD.
   - Structured logs, health checks, monitoring, and deployment documentation.

## 3. Required technology stack

Use this stack unless a documented technical constraint requires a change.

### Frontend
- Next.js with React and TypeScript.
- Tailwind CSS.
- shadcn/ui for reusable UI components.
- React Flow for workflow graph editing.
- TanStack Query for server state.
- React Hook Form and Zod for form validation.
- A charting library for actual API-backed analytics.

### Backend
- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy 2.x.
- Alembic.
- HTTPX.
- Pytest.
- Ruff for linting and formatting.
- Mypy or Pyright for type checking.

### Data and jobs
- PostgreSQL as the durable source of truth.
- Redis as the Celery broker.
- Celery for background jobs.
- Celery Beat or an equivalent scheduler only when scheduled triggers are implemented.

### AI and integrations
- Provider-neutral AI service interface.
- Structured outputs validated with Pydantic.
- SMTP or a transactional email API.
- HTTPX for external API requests.
- n8n as an optional external integration, not the core execution engine.

### Testing and operations
- Docker and Docker Compose.
- GitHub Actions.
- Playwright for end-to-end tests.
- Structured JSON logging.
- Sentry or an equivalent error-monitoring service when configured.
- OpenTelemetry-compatible instrumentation when practical.

Do not deploy Celery workers inside short-lived serverless request handlers. The API, worker, scheduler, and database must run on infrastructure suited to their responsibilities.

## 4. Architecture rules

Use a **modular monolith** for the first release. Keep a single FastAPI codebase with clearly separated modules. Do not introduce microservices or Kubernetes without a demonstrated need.

Use this request and execution flow:

1. Next.js calls FastAPI over HTTPS.
2. FastAPI authenticates the user and authorizes organization access.
3. Services validate inputs and apply business rules.
4. SQLAlchemy persists durable application state in PostgreSQL.
5. Background work is dispatched reliably to Celery through Redis.
6. Workers execute registered workflow nodes.
7. Results and failures are persisted to PostgreSQL.
8. The frontend reads execution and business state through the API.

Use a transactional outbox or another documented durable-dispatch approach where needed to prevent a database commit from succeeding while queue publication is lost.

Keep route handlers thin. Put business logic in services, persistence logic in repositories where useful, and workflow execution in a dedicated execution module.

Never execute arbitrary Python code supplied by a user or generated by an LLM.

## 5. Repository structure

Maintain a monorepo with a structure similar to:

```text
flowops-ai/
├── apps/
│   └── web/
│       ├── src/app/
│       ├── src/components/
│       ├── src/features/
│       │   ├── workflows/
│       │   ├── leads/
│       │   ├── executions/
│       │   ├── approvals/
│       │   └── integrations/
│       ├── src/hooks/
│       ├── src/lib/
│       └── src/types/
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/v1/
│       │   ├── core/
│       │   ├── db/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── repositories/
│       │   ├── services/
│       │   ├── workflows/
│       │   ├── execution/
│       │   ├── tasks/
│       │   ├── integrations/
│       │   ├── ai/
│       │   ├── security/
│       │   └── main.py
│       ├── migrations/
│       ├── tests/
│       └── pyproject.toml
├── infra/
│   ├── docker/
│   └── deployment/
├── docs/
├── scripts/
├── .github/workflows/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── CHATGPT.md
└── README.md
```

Adapt this structure to the repository if it already exists. Do not reorganize large parts of the project without a clear reason.

## 6. Core data model

Use UUID primary keys, timezone-aware timestamps, foreign keys, appropriate indexes, and database constraints. Every tenant-owned record must be scoped to an organization directly or through an enforceable relationship.

Create models and migrations for:

- `organizations`
- `users`
- `organization_memberships`
- `workflows`
- `workflow_versions`
- `leads`
- `import_jobs`
- `integrations`
- `workflow_executions`
- `execution_steps`
- `approval_requests`
- `webhook_events`
- `webhook_deliveries`
- `audit_logs`

### Important data rules

- Published workflow versions are immutable.
- Each execution records the exact workflow version it uses.
- Persist execution state and step results in PostgreSQL.
- Normalize email addresses before duplicate checks.
- Apply an explicit organization-scoped duplicate policy.
- Use uniqueness constraints for stable idempotency and provider event identifiers where appropriate.
- Store only non-secret integration settings in ordinary configuration JSON.
- Keep credentials in environment variables or a suitable secret store; encrypt stored credentials where needed.
- Do not log passwords, access tokens, API keys, or unnecessary personal data.
- Define file and record retention policies.

Create Alembic migrations for schema changes. Do not rely on automatic table creation in production.

## 7. Workflow graph and node system

Represent a workflow version as validated JSON containing:
- `schema_version`
- `nodes`
- `edges`

Each node must have a unique ID, a registered type, and validated configuration. Each edge must reference existing nodes and valid output handles.

Implement a backend node registry. Every node type must declare:
- Type identifier.
- Configuration schema.
- Input and output expectations.
- Validation function.
- Execution handler.
- Timeout policy.
- Retry classification.
- Side-effect classification.
- Required permissions.

Initial triggers:
- Manual.
- Lead created.
- Incoming webhook.
- Scheduled trigger.

Initial conditions:
- Equality.
- Contains.
- Numeric comparison.
- Field exists or is missing.
- Score threshold.

Initial actions:
- Validate lead.
- Detect duplicate.
- Score lead.
- Generate outreach draft.
- Request approval.
- Send email.
- Update lead status.
- Send internal notification.
- Delay or schedule a subsequent action.
- Record execution result.

Before publishing a workflow:
1. Validate schema version.
2. Check unique node IDs.
3. Reject unknown node types.
4. Validate each node's configuration.
5. Check all edges and handles.
6. Require a valid trigger.
7. Check required node connections.
8. Reject cycles unless a future bounded-loop feature explicitly supports them.
9. Check configured permissions.
10. Return actionable validation errors.

Use React Flow for the editor. The UI must support node palette, drag-and-drop, connections, node configuration, draft saving, validation, publishing, test runs, and unsaved-change warnings.

## 8. Execution engine requirements

The execution lifecycle must:
1. Authenticate and validate the trigger.
2. Check idempotency.
3. Load the published workflow version.
4. Persist an execution record.
5. Dispatch work durably.
6. Execute eligible nodes in dependency order.
7. Persist step input/output summaries and outcomes.
8. Schedule the next node, pause for approval, or finish.
9. Update status and relevant metrics.

Use explicit state transitions. Initial statuses:
- `queued`
- `running`
- `waiting_for_approval`
- `retrying`
- `succeeded`
- `failed`
- `cancelled`

### Reliability rules
- Assume queue messages and webhooks can be delivered more than once.
- Use database constraints and atomic state changes for deduplication.
- Apply bounded retries with exponential backoff and jitter.
- Do not retry validation failures automatically.
- Classify transient and permanent errors.
- Use timeouts for nodes and external calls.
- Record retry attempts and failure reasons.
- Persist approval checkpoints and resume from them.
- Support cancellation cooperatively.
- Use provider idempotency keys when supported.
- Reconcile uncertain external side effects before retrying when possible.
- Never claim exactly-once delivery across arbitrary external services.

A retry must not blindly repeat an external send that might already have succeeded.

## 9. Lead and AI requirements

### CSV import
- Enforce file type, size, and row-count limits.
- Validate column mappings.
- Normalize data.
- Report invalid rows.
- Detect duplicates within the file and against existing records.
- Apply a documented insert/update/skip policy.
- Process large files asynchronously.
- Store import progress and a downloadable or viewable error report.
- Clean up temporary files according to a retention policy.

### Deterministic lead scoring
Implement transparent rule-based scoring first. Example rules can include job-title fit, industry fit, company-size fit, valid business email, website presence, and missing required fields.

- Clamp scores to a documented range such as 0–100.
- Persist each applied rule and reason.
- Version the scoring profile.
- Keep the score reproducible.
- Do not treat example weights as validated business benchmarks.

### AI qualification and drafting
- Use a provider-neutral service interface.
- Use versioned prompts.
- Validate model outputs with Pydantic.
- Distinguish verified facts from missing or inferred information.
- Treat imported text and external content as untrusted.
- Handle provider timeout, rate limiting, invalid output, and outages.
- Record appropriate provider/model/usage metadata.
- Minimize personal data sent to AI providers.
- Do not let AI control permissions or bypass business rules.
- Keep non-AI workflows functional if the provider is unavailable.

### Human approval
For protected external communication:
1. Generate and validate a draft.
2. Persist the draft and approval request.
3. Pause the execution.
4. Show the draft and relevant context to an authorized user.
5. Record approval or rejection transactionally.
6. Verify the decision is current and authorized.
7. Resume or terminate the execution.

Provide a mock email adapter for local development. Never silently send real email from demo mode.

## 10. Integrations and webhooks

Implement a small number of reliable integrations before adding more providers.

Required:
- AI provider adapter.
- Email provider adapter or SMTP adapter.
- One real external service integration selected based on available credentials.
- Incoming webhook endpoint.
- Outgoing webhook delivery with history and retries.
- Optional n8n webhook integration.

Rules:
- Keep provider code behind adapter interfaces.
- Use HTTP timeouts and handle rate limits.
- Verify signatures when the provider supports them.
- Deduplicate incoming events using stable event IDs when available.
- Record outgoing delivery attempts.
- Redact secrets from logs and API responses.
- Validate outbound destinations to prevent SSRF.
- Block loopback/private network targets unless explicitly authorized.
- Revalidate destinations after redirects and restrict protocols.
- Never expose credentials to the frontend.
- Implement OAuth only if the selected provider requires it.

## 11. API requirements

Use `/api/v1` and FastAPI's OpenAPI documentation.

Implement routes for:
- Current user and organizations.
- Organization members and roles.
- Workflow CRUD, validation, publication, pause/resume, versions, and test runs.
- Lead CRUD, search, imports, scoring, and draft generation.
- Execution listing, detail, steps, retry, and cancellation.
- Approval listing, detail, approval, and rejection.
- Integration CRUD, connection tests, and disablement.
- Incoming webhooks and outgoing delivery history/retries.
- Liveness and readiness health checks.

Use Pydantic request/response schemas, correct HTTP status codes, consistent error responses, pagination, correlation IDs, rate limiting, and appropriate idempotency keys.

For every route:
- Verify authentication.
- Verify organization membership.
- Enforce the required role or permission.
- Validate referenced resources belong to the same organization.
- Avoid leaking internal stack traces.

Do not claim a route exists until it has been implemented and tested.

## 12. Frontend requirements

Create a clean, responsive SaaS dashboard with navigation for:
- Overview.
- Workflows.
- Leads.
- Executions.
- Approvals.
- Integrations.
- Team and settings.

### Overview
Use actual API data for lead totals, active workflows, execution counts, success/failure information, pending approvals, and recent activity. Do not present hardcoded sample metrics as live results.

### Workflows
Show name, status, last execution, execution counts, and actions allowed for the current user.

### Leads
Show searchable and filterable lead records, scores, qualification reasons, import history, and outreach drafts.

### Executions
Show status, workflow version, trigger, timestamps, duration, node timeline, retries, and safe error summaries.

### Approvals
Show the requested action, draft content, context, workflow, and approval history. Provide approve/reject actions with appropriate confirmation.

### Integrations
Show provider, connection status, last test, non-secret configuration, and test/disable actions. Never render stored secrets back into the UI.

All pages must implement loading, empty, error, success, and permission-denied states. Ensure keyboard accessibility, visible focus states, labels, responsive layouts, and useful error messages.

## 13. Security rules

Security is a release requirement.

- Enforce organization isolation in the backend.
- Centralize role and permission checks.
- Prevent insecure direct object references.
- Validate all input server-side.
- Keep secrets out of source control.
- Use a maintained authentication implementation.
- Apply request-size limits and rate limiting.
- Verify webhook signatures where supported.
- Protect against replay and duplicate events where applicable.
- Restrict outbound URLs to prevent SSRF.
- Treat AI input and output as untrusted.
- Require approval for protected external side effects.
- Redact sensitive data from logs.
- Restrict audit-log access.
- Define retention and deletion rules.
- Test cross-organization access explicitly.

Do not implement custom cryptography or an authentication system from scratch without a documented and justified need.

## 14. Testing and quality gates

### Unit tests
Cover scoring, normalization, graph validation, node configuration, permission policies, retry classification, idempotency, AI output validation, and error handling.

### Integration tests
Cover API/database behavior, migrations, Redis/Celery jobs, workflow state transitions, approval resumption, webhook validation, integration failures, and tenant isolation.

Use PostgreSQL for tests involving PostgreSQL-specific constraints or behavior. SQLite is not a complete substitute.

### End-to-end tests
Use Playwright for the critical journey:
1. Sign in.
2. Create a workflow.
3. Validate and publish it.
4. Import leads.
5. Run the workflow.
6. Generate an AI draft.
7. Approve or reject it.
8. Execute a mock or configured integration.
9. Inspect execution results.

Also test failure and retry, duplicate webhook delivery, invalid CSV, and unauthorized access.

### CI checks
Run relevant checks on pull requests:
- Ruff.
- Python type checks.
- Pytest.
- Frontend lint.
- TypeScript checks.
- Frontend build.
- Integration tests where practical.
- Dependency/security checks.

Do not claim a test passed unless it was run and its result was inspected. Fix regressions before moving on.

## 15. DevOps and deployment

Provide:
- Dockerfiles for the frontend and backend where appropriate.
- Docker Compose for local development with PostgreSQL, Redis, API, worker, and frontend.
- `.env.example` with placeholders only.
- Alembic migrations.
- GitHub Actions workflows.
- Separate development and production configuration.
- Health/readiness endpoints.
- Structured logs and correlation IDs.
- Deployment and rollback instructions.
- PostgreSQL backup and restore instructions.
- Worker and queue monitoring guidance.

Deploy the frontend to Vercel if suitable. Deploy the FastAPI API and persistent background workers to infrastructure that supports them. Do not assume Vercel serverless functions are suitable for long-running Celery workers.

Use controlled database migration steps. Test the deployed application with smoke tests. Never report a successful deployment without verifying it.

## 16. Documentation to maintain

Create and keep updated:
- `README.md` — overview and local setup.
- `docs/PRD.md` — product requirements.
- `docs/SRS.md` — functional and non-functional requirements.
- `docs/TRD.md` — technical decisions and implementation details.
- `docs/ARCHITECTURE.md` — architecture and data flows.
- `docs/API.md` — API conventions and endpoint overview.
- `docs/DATABASE.md` — schema, constraints, and indexes.
- `docs/SECURITY.md` — authentication, authorization, secrets, and threat controls.
- `docs/TESTING.md` — test strategy and commands.
- `docs/DEPLOYMENT.md` — deployment procedure.
- `docs/RUNBOOK.md` — troubleshooting and recovery.
- Architecture decision records for significant choices.

Documentation must describe the code that exists, not aspirational features presented as complete.

## 17. Milestone plan

Work in this order. Each milestone must pass its acceptance criteria before the next one begins.

### Milestone 0 — Repository inspection and plan
- Inspect existing files and environment.
- Identify available runtimes and tools.
- Confirm repository structure and package managers.
- Write a concise implementation plan.
- Do not overwrite existing work without inspecting it.

### Milestone 1 — Foundation
- Set up frontend and FastAPI.
- Configure PostgreSQL, Redis, Docker Compose, and environment validation.
- Implement authentication and organization membership.
- Implement lead CRUD and database migrations.
- Add initial tests and CI checks.

**Acceptance:** The app starts from documented commands, persists leads, and blocks unauthorized cross-organization access.

### Milestone 2 — Workflow builder
- Define graph schema and node registry.
- Implement graph validation.
- Implement draft saving and immutable published versions.
- Build React Flow editor.
- Add workflow templates and test-run interface.

**Acceptance:** A user can create, validate, save, publish, and inspect a workflow.

### Milestone 3 — Execution engine
- Add Celery worker.
- Persist execution and step state.
- Implement deterministic node execution.
- Add retry classification, timeouts, idempotency, and failure history.
- Add approval pause/resume support.

**Acceptance:** Work executes outside the request process, results persist, and eligible failures follow the retry policy.

### Milestone 4 — AI and lead operations
- Implement CSV import.
- Implement duplicate policy and deterministic scoring.
- Add structured AI qualification and draft generation.
- Add approval inbox.
- Add mock email adapter.

**Acceptance:** A lead can be imported, scored, drafted, approved, and processed through an inspectable execution.

### Milestone 5 — Integrations and webhooks
- Add one real external integration.
- Add inbound webhook verification and deduplication.
- Add outgoing webhook delivery tracking and retries.
- Add integration health checks and safe credential configuration.

**Acceptance:** Integration success and failure are visible, and duplicate events are handled safely.

### Milestone 6 — Production readiness
- Complete unit, integration, and end-to-end tests.
- Complete CI/CD.
- Deploy frontend, API, database, and workers appropriately.
- Add monitoring, health checks, backup/recovery instructions, and documentation.
- Record a complete demo.

**Acceptance:** A clean setup follows the README, CI passes, the deployed app is healthy, and the end-to-end demo works.

## 18. Required end-to-end demo

Demonstrate this complete scenario:

1. Sign in to an organization.
2. Create and publish a workflow: Lead Created → Validate → Deduplicate → Score → Condition → Generate Draft → Approval → Send Email → Record Result.
3. Import a sample CSV containing valid, invalid, and duplicate rows.
4. Show row-level import results.
5. Run the workflow and inspect background execution.
6. Show the score and reasons.
7. Generate a personalized draft from verified fields.
8. Show the workflow paused for approval.
9. Approve the draft as an authorized user.
10. Send through the configured provider or use the explicit mock adapter.
11. Inspect execution steps, delivery result, duration, and logs.
12. Simulate a transient failure and show the retry behavior.
13. Demonstrate that an unauthorized user cannot approve or access another organization's records.

Use fictional or authorized sample data. Clearly label demo mode and never send real external messages without an explicit user action and configured approval policy.

## 19. Coding-agent working protocol

For each task:

1. Inspect relevant source files and documentation.
2. State the specific goal and acceptance criteria briefly.
3. Identify affected files and potential risks.
4. Implement the smallest coherent change.
5. Add or update tests.
6. Run relevant tests, linting, type checks, and builds.
7. Inspect the output and fix failures.
8. Update documentation if behavior or configuration changed.
9. Summarize files changed, commands run, verified results, and remaining limitations.

Do not:
- Generate the entire application in one unreviewed change.
- Replace real features with static mock screens.
- Add dependencies without a reason.
- Suppress failing tests to make a build pass.
- hardcode credentials or production URLs.
- silently change the selected stack.
- claim unverified integrations, tests, metrics, or deployments.
- start future milestones while critical current-milestone checks fail.

If a provider credential is unavailable, implement a clear adapter interface and a safe mock for development. Document what needs credentials; do not pretend the real integration has been verified.

## 20. Definition of done

Version 1 is complete when:
- Authentication and organization-level authorization work.
- Workflow drafts can be validated and published as immutable versions.
- Leads can be imported and scored with transparent reasons.
- AI drafts are schema-validated and require approval before protected external sends.
- Background jobs persist state and recover safely from eligible failures.
- Idempotency protections exist for supported operations.
- Integrations and webhook delivery attempts are inspectable.
- Execution logs and audit records are available to authorized users.
- Critical flows have automated tests.
- Docker-based local setup works.
- CI runs required checks.
- The application and worker processes are deployed and monitored.
- Setup, architecture, API, security, testing, deployment, and recovery docs are complete.
- A recorded end-to-end demonstration works.

**Start now with Milestone 0. Inspect the repository and environment first. Do not jump ahead or claim anything is implemented until it has been built and verified.**
