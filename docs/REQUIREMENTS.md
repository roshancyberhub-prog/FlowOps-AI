# FlowOps AI
## Product Requirements, Technical Specification, System Architecture, and Implementation Plan

**Document type:** PRD + TRD + Software Requirements Specification + Implementation Guide  
**Product:** FlowOps AI  
**Version:** 1.0  
**Project type:** Full-stack SaaS application  
**Primary objective:** Build a production-style workflow automation and AI-powered lead operations platform for a software engineering portfolio.

---

# 1. Project Overview

## 1.1 Product vision

FlowOps AI is a workflow automation and operations platform that enables businesses to create automated processes, manage leads, connect external applications, execute background jobs, and monitor automation activity from one dashboard.

The platform combines:

- Visual workflow creation.
- AI-assisted lead qualification.
- Background job processing.
- API and webhook integrations.
- Human approval controls.
- Execution logs and monitoring.
- Secure multi-user access.
- Automated testing and deployment.

The application must operate as a real software product, not a static dashboard or a collection of mockups.

## 1.2 Problem statement

Businesses often manage leads, CRM updates, notifications, and follow-ups across disconnected applications.

This creates several problems:

1. Repetitive manual work.
2. Duplicate or invalid lead records.
3. Inconsistent lead qualification.
4. Failed automations without clear error reports.
5. Duplicate actions when webhooks are delivered more than once.
6. Poor visibility into automation performance.
7. Limited control over AI-generated external communications.

FlowOps AI addresses these problems through configurable workflows, deterministic execution, AI assistance, approval steps, and centralized monitoring.

## 1.3 Primary users

### Business owner
- Reviews business operations.
- Monitors automation performance.
- Manages team members and permissions.

### Sales or operations manager
- Imports leads.
- Defines lead qualification rules.
- Reviews AI-generated messages.
- Approves or rejects external communications.

### Automation administrator
- Creates workflows.
- Configures integrations.
- Investigates failed executions.
- Manages retries and workflow versions.

### Developer
- Uses the REST API and webhooks.
- Configures integrations.
- Inspects execution records.
- Troubleshoots application errors.

## 1.4 Main product workflow

Example: A business receives a new lead.

1. A lead enters through CSV import or an authenticated API.
2. The backend validates the lead data.
3. The application detects duplicate records.
4. The lead is saved to PostgreSQL.
5. A configured workflow receives the event.
6. A background worker evaluates workflow conditions.
7. The system calculates a lead score.
8. An AI service drafts a personalized follow-up.
9. The execution pauses for human approval.
10. An authorized user approves or rejects the draft.
11. An integration sends the approved message or records a simulated send in development mode.
12. The system records the result and updates the dashboard.

Every step must have an execution record, a defined outcome, and an appropriate error-handling path.

---

# 2. Scope and Core Modules

The product consists of five required modules.

## Module 1: Workflow Builder

Users create and manage workflows using triggers, conditions, actions, and approval steps.

Required capabilities:

- Create, edit, duplicate, publish, pause, and archive workflows.
- Build workflows from predefined templates.
- Add triggers, conditions, and actions.
- Connect nodes in a visual editor.
- Configure node parameters.
- Validate workflow definitions.
- Save drafts separately from published versions.
- Inspect workflow execution history.
- Test workflows using sample events.
- Prevent invalid or cyclic workflow graphs.
- Show validation errors before publication.

Initial supported triggers:

- Manual execution.
- New lead created.
- Webhook received.
- Scheduled trigger.

Initial supported conditions:

- Field equals a value.
- Field contains text.
- Numeric comparison.
- Field exists or is missing.
- Lead score meets a threshold.

Initial supported actions:

- Validate lead.
- Check for duplicates.
- Calculate lead score.
- Generate AI message draft.
- Create approval request.
- Send email.
- Update lead status.
- Send internal notification.
- Delay or schedule a subsequent action.
- Write execution result.

The visual editor should use React Flow. Store workflow definitions as versioned JSON graphs.

## Module 2: AI-Powered Lead Operations

Users manage leads and apply AI-assisted qualification and outreach.

Required capabilities:

- CSV lead import.
- Lead creation and editing.
- Email format validation.
- Duplicate detection.
- Configurable ideal customer profile (ICP).
- Rule-based lead scoring.
- AI-assisted lead qualification.
- AI-generated personalized follow-up drafts.
- Human approval before external sending.
- Lead status and qualification reason.
- Bulk processing.
- Import error reports.
- Search, filters, and pagination.
- Import and processing history.

Lead scoring must use deterministic rules as the baseline. The LLM may provide additional analysis, but it must not silently override the defined scoring rules.

Example lead fields:

- Name.
- Work email.
- Company.
- Job title.
- Website.
- Industry.
- Company size.
- Country.
- Lead source.
- Lead status.
- Score.
- Qualification reasons.
- Created date.

Use structured AI responses validated with Pydantic. Treat imported data and external content as untrusted input.

## Module 3: Reliable Execution Engine

The execution engine runs workflows in the background and maintains their state.

Required capabilities:

- Asynchronous job processing.
- Persistent execution records.
- Step-by-step execution history.
- Retry policies.
- Configurable execution timeouts.
- Exponential backoff.
- Idempotency protection.
- Failure handling.
- Execution cancellation where safe.
- Dead-letter handling for exhausted retries.
- Human approval pauses and resumptions.
- Worker health monitoring.
- Execution duration tracking.
- Error summaries and stack traces restricted to authorized administrators.

Initial execution statuses:

- queued
- running
- waiting_for_approval
- retrying
- succeeded
- failed
- cancelled

A workflow execution must not rely on a browser session remaining open. Background workers must continue processing independently.

The system must persist execution state so that a worker restart does not erase job history.

## Module 4: Integrations and Webhooks

The platform connects external applications through documented APIs.

Required capabilities:

- REST API.
- Incoming webhooks.
- Outgoing webhooks.
- Email integration.
- AI provider integration.
- One real external service integration.
- Integration configuration and health status.
- Secret management.
- Connection testing.
- Webhook delivery history.
- Retry handling for transient failures.
- Signature validation where supported.
- API rate limiting.

Recommended initial integrations:

1. An LLM provider for AI qualification and message drafting.
2. An email provider supporting an API or SMTP.
3. A project management or CRM service for one real integration.
4. An optional n8n webhook for external automation.

Select the external CRM or project management provider based on available credentials and API access.

Start with API keys where appropriate. Implement OAuth only when required by the chosen provider.

Never expose provider credentials to the frontend.

## Module 5: Production-Ready Engineering

The application must include software engineering practices expected of a deployed application.

Required capabilities:

- User authentication.
- Organization-based data isolation.
- Role-based access control.
- Input validation.
- Secure secret storage.
- Rate limiting.
- Audit logs.
- Database migrations.
- Structured application logging.
- Automated tests.
- Docker-based local development.
- Continuous integration.
- Deployment configuration.
- Health checks.
- Error monitoring.
- API documentation.
- Backup and recovery guidance.
- Environment-specific configuration.

The application must enforce permissions in the backend. Hiding a button in the frontend does not provide security.

---

# 3. Technology Stack

Use a consistent stack. Avoid adding unnecessary frameworks before the core application works.

## 3.1 Frontend

**Next.js + React + TypeScript**

Supporting technologies:

- Tailwind CSS.
- shadcn/ui for reusable interface components.
- React Flow for the visual workflow editor.
- TanStack Query for server state and request caching.
- React Hook Form for forms.
- Zod for client-side validation.
- A charting library for execution analytics.

Responsibilities:

- Render the dashboard.
- Manage workflow editing interactions.
- Display leads and import reports.
- Show execution status and logs.
- Submit approval decisions.
- Configure integrations.
- Handle loading, empty, and error states.

Do not treat client-side state as the authoritative source for workflow status or permissions.

## 3.2 Backend

**Python + FastAPI**

Supporting technologies:

- Pydantic for request and response validation.
- SQLAlchemy 2.x for database access.
- Alembic for schema migrations.
- Pytest for testing.
- HTTPX for external HTTP requests and API tests.
- A maintained authentication library or identity provider integration.

Responsibilities:

- Authenticate requests.
- Authorize organization access.
- Validate business data.
- Expose REST endpoints.
- Manage workflow definitions.
- Schedule execution jobs.
- Execute workflow nodes.
- Manage approvals.
- Call external APIs.
- Record audit events.

Use a modular monolith for the first version. Keep the backend in one deployable application with clear internal modules. Split services only when a real scaling or isolation requirement emerges.

## 3.3 Database

**PostgreSQL**

Use PostgreSQL for:

- Organizations and users.
- Workflow definitions and versions.
- Leads and import jobs.
- Integration metadata.
- Execution records.
- Execution steps.
- Approval requests.
- Webhook event records.
- Audit logs.

Store workflow graphs in validated JSONB columns where suitable. Use relational tables for entities requiring relationships, constraints, and frequent querying.

Add database indexes for organization IDs, execution statuses, creation timestamps, lead email lookups, and other demonstrated query patterns.

## 3.4 Background processing

**Redis + Celery**

Redis acts as the message broker and supports distributed background processing.

Celery handles:

- Workflow execution jobs.
- Lead import processing.
- AI processing tasks.
- Scheduled jobs.
- Retryable integration calls.
- Outgoing webhook deliveries.

Use PostgreSQL as the source of truth for business state. Redis must not be the only place where execution history or approval state exists.

Celery Beat or an equivalent scheduler may be used for recurring jobs. Keep scheduling configuration explicit.

## 3.5 AI

Use a provider-neutral AI service interface.

Responsibilities:

- Lead qualification.
- Outreach drafting.
- Structured response generation.
- Prompt versioning.
- Token usage tracking.
- Error handling.
- Provider timeout management.

The application must continue to support non-AI workflows if the LLM provider is unavailable.

Do not use an LLM to decide whether the user has permission to perform an action.

## 3.6 Integrations

Use:

- HTTPX for outbound API calls.
- SMTP or a transactional email API for email.
- Signed webhooks where supported.
- n8n as an optional external automation system.
- Provider-specific adapters behind common internal interfaces.

## 3.7 DevOps and quality

Use:

- Docker.
- Docker Compose.
- GitHub Actions.
- Ruff for Python linting and formatting.
- Mypy or Pyright for useful static type checks.
- Pytest.
- Playwright for end-to-end browser tests.
- Structured JSON logs.
- OpenTelemetry-compatible instrumentation when practical.
- Sentry or an equivalent error-monitoring service.

Host the frontend on Vercel if suitable. Host FastAPI, workers, Redis, and PostgreSQL on infrastructure that supports persistent processes and background jobs. Do not run Celery workers inside a short-lived serverless request handler.

---

# 4. High-Level Architecture

## 4.1 Logical architecture

```text
                 USERS
                   |
                   v
          Next.js Web Application
                   |
             HTTPS / REST
                   |
                   v
             FastAPI Backend
                   |
       +-----------+------------+
       |           |            |
       v           v            v
 Authentication  Workflow     Lead
 and RBAC        Service      Service
       |           |            |
       +-----------+------------+
                   |
                   v
              PostgreSQL
                   |
          Durable job dispatch
                   |
                   v
             Redis Broker
                   |
                   v
             Celery Workers
                   |
       +-----------+------------+
       |           |            |
       v           v            v
    Workflow       AI         Integration
    Executor     Provider      Adapters
       |           |            |
       +-----------+------------+
                   |
                   v
         Execution and Audit Logs
                   |
                   v
          Dashboard and Alerts
```

This diagram represents logical responsibilities. It does not require each module to be a separate microservice.

## 4.2 Repository structure

Use a monorepo.

```text
flowops-ai/
├── apps/
│   └── web/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/
│       │   │   ├── workflows/
│       │   │   ├── leads/
│       │   │   ├── executions/
│       │   │   ├── approvals/
│       │   │   └── integrations/
│       │   ├── hooks/
│       │   ├── lib/
│       │   └── types/
│       └── package.json
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   │   └── v1/
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
│       ├── pyproject.toml
│       └── Dockerfile
├── infra/
│   ├── docker/
│   └── deployment/
├── docs/
│   ├── PRD.md
│   ├── SRS.md
│   ├── TRD.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATABASE.md
│   ├── SECURITY.md
│   ├── TESTING.md
│   ├── DEPLOYMENT.md
│   └── RUNBOOK.md
├── scripts/
├── .github/
│   └── workflows/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Keep framework-specific code inside the relevant application. Do not place database logic, workflow execution, or external provider logic directly inside route handlers.

---

# 5. Functional Requirements

## FR-001: User authentication

The system must support secure sign-in and sign-out.

Requirements:

- Validate credentials or delegate authentication to an identity provider.
- Create or retrieve the user's organization membership.
- Enforce authorization on every protected API.
- Prevent cross-organization access.
- Support session expiration and revocation.
- Provide a controlled invitation process if team invitations are implemented.

Use a maintained authentication solution. Avoid implementing password hashing, token rotation, or session management from scratch without a clear reason.

## FR-002: Organization management

A user belongs to an organization or workspace.

Requirements:

- Create an organization.
- Add authorized members.
- Assign roles.
- Restrict access to organization-owned resources.
- Record membership and role changes in the audit log.

Initial roles:

- Owner.
- Admin.
- Member.
- Viewer.

Define the permissions for each role in a centralized policy module.

## FR-003: Workflow management

Users must be able to create workflows and save drafts.

Requirements:

- Validate graph structure.
- Ensure node IDs are unique.
- Validate node configuration against the selected node type.
- Ensure connected nodes exist.
- Detect cycles unless an explicit bounded-loop feature is implemented.
- Require valid start triggers.
- Require valid connections between nodes.
- Create immutable published versions.
- Prevent editing an already published version in place.
- Allow an execution to continue using the version with which it started.

## FR-004: Lead management

Requirements:

- Create, read, update, and archive leads.
- Import CSV files.
- Validate input.
- Detect duplicates within an import.
- Detect duplicates against existing organization records.
- Report invalid rows.
- Support pagination and filtering.
- Store scoring results and reasons.
- Track lead status changes.

Define a duplicate policy. A reasonable initial rule is case-insensitive normalized email matching within the same organization. Do not silently merge conflicting records.

## FR-005: Workflow execution

Requirements:

- Accept an execution request.
- Persist an execution record.
- Queue background work.
- Execute nodes in dependency order.
- Store node input and output summaries.
- Record success or failure.
- Retry eligible failures.
- Enforce timeouts and execution limits.
- Support approval pauses.
- Resume from a persisted checkpoint.
- Prevent duplicate external side effects when an operation is retried.

## FR-006: AI operations

Requirements:

- Validate AI input.
- Use versioned prompts.
- Request structured outputs.
- Validate model output.
- Handle timeouts and rate limits.
- Record model and usage metadata where appropriate.
- Provide a safe fallback when AI is unavailable.
- Require approval before external outreach.
- Avoid placing unnecessary personal information in model prompts.

## FR-007: Integrations

Requirements:

- Store connection metadata securely.
- Test connectivity.
- Validate incoming webhook signatures when available.
- Deduplicate webhook deliveries.
- Retry eligible outbound requests.
- Record delivery attempts.
- Handle provider-specific rate limits.
- Allow an integration to be disabled without deleting historical records.

## FR-008: Observability

Requirements:

- Record structured logs.
- Provide execution detail pages.
- Track failure counts and durations.
- Show queue and worker health where available.
- Record correlation IDs.
- Provide health endpoints.
- Prevent secrets and sensitive message content from appearing in logs.

## FR-009: Auditability

Record important actions, including:

- Login and authentication events where available.
- Workflow publication.
- Workflow execution.
- Approval decisions.
- Integration configuration changes.
- Lead modifications.
- Member and role changes.
- Retry and cancellation actions.

Audit records should be append-only through normal application operations. Restrict access to audit data.

---

# 6. Database Design

Use SQLAlchemy models and Alembic migrations. Every organization-owned record must include an organization identifier directly or through an enforceable relationship.

The following is the initial logical schema.

## 6.1 organizations

Fields:

- id: UUID primary key.
- name: string.
- slug: unique workspace identifier.
- created_at: timestamp.
- updated_at: timestamp.

## 6.2 users

Fields:

- id: UUID primary key.
- email: normalized email address.
- display_name: string.
- identity_provider_id: nullable external identity reference.
- created_at: timestamp.
- updated_at: timestamp.

## 6.3 organization_memberships

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- user_id: foreign key.
- role: enum.
- status: enum.
- created_at: timestamp.

Constraint: unique organization_id and user_id pair.

## 6.4 workflows

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- name: string.
- description: nullable text.
- status: draft, active, paused, archived.
- current_version_id: nullable foreign key.
- created_by: user foreign key.
- created_at: timestamp.
- updated_at: timestamp.

## 6.5 workflow_versions

Fields:

- id: UUID primary key.
- workflow_id: foreign key.
- version_number: integer.
- graph_definition: JSONB.
- validation_errors: JSONB, if useful for draft validation.
- created_by: user foreign key.
- created_at: timestamp.

Constraint: unique workflow_id and version_number pair.

Published versions are immutable.

## 6.6 leads

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- name: string.
- email_normalized: nullable string.
- company: nullable string.
- job_title: nullable string.
- website: nullable string.
- industry: nullable string.
- company_size: nullable string.
- country: nullable string.
- source: nullable string.
- status: enum.
- score: integer.
- score_reasons: JSONB.
- metadata: JSONB.
- created_at: timestamp.
- updated_at: timestamp.

Use a suitable organization-scoped index for normalized email lookup. If the business rule permits only one record per email, use an appropriate unique constraint for non-null values.

## 6.7 import_jobs

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- uploaded_by: user foreign key.
- original_filename: string.
- status: enum.
- total_rows: integer.
- processed_rows: integer.
- success_rows: integer.
- failed_rows: integer.
- error_report_location: nullable string.
- created_at: timestamp.
- completed_at: nullable timestamp.

Do not store uploaded CSV files indefinitely without a retention policy.

## 6.8 integrations

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- provider: string.
- display_name: string.
- status: enum.
- credential_reference: nullable string.
- configuration: JSONB containing non-secret settings.
- last_tested_at: nullable timestamp.
- created_at: timestamp.
- updated_at: timestamp.

Do not store plaintext credentials in the configuration JSON.

## 6.9 workflow_executions

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- workflow_id: foreign key.
- workflow_version_id: foreign key.
- status: enum.
- trigger_type: string.
- trigger_reference: nullable string.
- input_summary: JSONB.
- output_summary: JSONB.
- idempotency_key: nullable string.
- attempt_count: integer.
- started_at: nullable timestamp.
- completed_at: nullable timestamp.
- error_code: nullable string.
- error_summary: nullable text.
- created_at: timestamp.

Use a database constraint for the appropriate organization-scoped idempotency rule.

## 6.10 execution_steps

Fields:

- id: UUID primary key.
- execution_id: foreign key.
- node_id: string.
- attempt_number: integer.
- status: enum.
- input_summary: JSONB.
- output_summary: JSONB.
- error_code: nullable string.
- error_summary: nullable text.
- started_at: nullable timestamp.
- completed_at: nullable timestamp.
- duration_ms: nullable integer.

Constraint: unique execution_id, node_id, and attempt_number.

## 6.11 approval_requests

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- execution_id: foreign key.
- execution_step_id: foreign key.
- status: pending, approved, rejected, expired.
- requested_action: string.
- payload_summary: JSONB.
- requested_at: timestamp.
- decided_by: nullable user foreign key.
- decided_at: nullable timestamp.
- decision_comment: nullable text.

Approval decisions must be authorized and recorded transactionally.

## 6.12 webhook_events

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- integration_id: nullable foreign key.
- provider_event_id: nullable string.
- event_type: string.
- payload_hash: string.
- processing_status: enum.
- received_at: timestamp.
- processed_at: nullable timestamp.
- error_summary: nullable text.

Use a uniqueness rule based on the provider's stable event identifier where available.

## 6.13 webhook_deliveries

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- execution_id: nullable foreign key.
- destination_reference: string.
- payload_summary: JSONB.
- status: enum.
- attempt_count: integer.
- next_attempt_at: nullable timestamp.
- last_http_status: nullable integer.
- last_error: nullable text.
- created_at: timestamp.
- completed_at: nullable timestamp.

## 6.14 audit_logs

Fields:

- id: UUID primary key.
- organization_id: foreign key.
- actor_user_id: nullable foreign key.
- action: string.
- resource_type: string.
- resource_id: nullable string.
- correlation_id: nullable string.
- metadata: JSONB.
- created_at: timestamp.

Never place passwords, access tokens, full credentials, or unnecessary sensitive data in audit metadata.

---

# 7. Workflow Graph Specification

Represent each workflow version as a JSON graph.

Example:

```json
{
  "schema_version": 1,
  "nodes": [
    {
      "id": "trigger_1",
      "type": "trigger.lead_created",
      "config": {}
    },
    {
      "id": "score_1",
      "type": "action.score_lead",
      "config": {
        "scoring_profile": "default"
      }
    },
    {
      "id": "condition_1",
      "type": "condition.score_threshold",
      "config": {
        "operator": "gte",
        "value": 70
      }
    },
    {
      "id": "draft_1",
      "type": "action.generate_email_draft",
      "config": {
        "template": "initial_follow_up"
      }
    },
    {
      "id": "approval_1",
      "type": "action.request_approval",
      "config": {}
    }
  ],
  "edges": [
    {
      "source": "trigger_1",
      "target": "score_1"
    },
    {
      "source": "score_1",
      "target": "condition_1"
    },
    {
      "source": "condition_1",
      "sourceHandle": "true",
      "target": "draft_1"
    },
    {
      "source": "draft_1",
      "target": "approval_1"
    }
  ]
}
```

The example illustrates the format. The final schema must define condition outputs, required configuration, valid edge types, and failure behavior.

## 7.1 Node registry

Implement a backend node registry.

Each node type must declare:

- Unique type identifier.
- Configuration schema.
- Input requirements.
- Output schema.
- Validation function.
- Execution handler.
- Retry classification.
- Timeout policy.
- Side-effect classification.
- Required permissions.

Example interface:

```python
class WorkflowNodeHandler:
    def validate_config(self, config: dict) -> None:
        ...

    async def execute(self, context):
        ...
```

Use typed protocols or equivalent interfaces in the actual implementation.

Never execute arbitrary Python code supplied in a workflow definition.

## 7.2 Graph validation

Before publication:

1. Validate the graph schema version.
2. Validate unique node IDs.
3. Validate node types against the registry.
4. Validate node configuration.
5. Validate edges.
6. Validate trigger count and placement.
7. Check for invalid cycles.
8. Check required connections.
9. Check permissions for configured actions.
10. Save validation results.

A valid workflow must have a deterministic execution plan.

## 7.3 Visual editor requirements

The editor must provide:

- Node palette.
- Drag-and-drop nodes.
- Connectable edges.
- Node configuration panel.
- Workflow name and status.
- Save draft action.
- Validate action.
- Publish action.
- Test-run action.
- Unsaved-change warning.
- Clear validation messages.

Start with a fixed set of node types. Do not build an unrestricted general-purpose programming language.

---

# 8. Execution Engine Design

## 8.1 Execution lifecycle

The execution lifecycle is:

1. Receive a trigger.
2. Authenticate and validate the event.
3. Check idempotency.
4. Load the published workflow version.
5. Create the execution record.
6. Commit the record and dispatch intent.
7. Enqueue the execution job.
8. Load execution state in the worker.
9. Execute the next eligible node.
10. Persist the node result.
11. Schedule the next node or wait for approval.
12. Mark the execution terminal when appropriate.
13. Update metrics and notify authorized users.

Use a transactional outbox pattern or another durable dispatch strategy so a database commit and queue publication failure do not silently lose execution jobs.

## 8.2 Idempotency

Assume webhook events and queue jobs might be delivered more than once.

Implement:

- Unique event identifiers where available.
- Database uniqueness constraints.
- Organization-scoped idempotency keys.
- Atomic claims or locks where needed.
- Persisted step states.
- Idempotent internal actions.

For external side effects, pass an idempotency key to the provider if supported.

Do not claim exactly-once execution across arbitrary external services. Explain the delivery and retry guarantees for each integration.

## 8.3 Retry policy

Recommended initial policy:

- Maximum of three attempts for eligible transient errors.
- Exponential backoff with jitter.
- Per-step timeout.
- Overall execution timeout.
- No automatic retries for validation failures.
- No automatic retries for permanent authorization failures.
- Dead-letter state after retry exhaustion.

Make retry limits configurable within safe bounds.

Before retrying a side-effecting operation, determine whether the previous attempt might have succeeded. Use provider idempotency support or reconciliation where possible.

## 8.4 Human approval

When a workflow reaches an approval node:

1. Persist the execution checkpoint.
2. Create an approval request.
3. Set the execution status to waiting_for_approval.
4. Notify authorized users.
5. Display the requested action and its relevant payload.
6. Record the approval decision.
7. Verify authorization and request status.
8. Resume or terminate the execution.

Reject stale decisions and concurrent conflicting approvals.

Never send external outreach before the approval gate when approval is required by policy.

## 8.5 Cancellation

Cancellation must be cooperative.

- Do not start new steps after a cancellation is confirmed.
- Stop eligible queued work.
- Record cancellation requests.
- Handle in-progress external requests carefully.
- Never imply that a completed external side effect has been reversed.

## 8.6 Execution monitoring

Each execution page must display:

- Workflow name and version.
- Trigger source.
- Current status.
- Start and end timestamps.
- Total duration.
- Node sequence.
- Per-step duration.
- Retry attempts.
- Approval status.
- Error summaries.
- Correlation ID.

---

# 9. AI Lead Operations Specification

## 9.1 CSV import

The import pipeline must:

1. Accept an allowed CSV file type.
2. Apply file-size and row-count limits.
3. Validate column mapping.
4. Normalize input.
5. Validate email format.
6. Detect duplicate rows within the file.
7. Check duplicates in the database.
8. Insert or update according to the configured policy.
9. Store row-level processing results.
10. Generate an import summary.

Use background processing for large files. Do not load an unrestricted file entirely into application memory.

## 9.2 Lead scoring

Implement a configurable baseline scoring system.

Example scoring rules:

| Signal | Example score |
|---|---:|
| Job title matches a target decision-maker | +25 |
| Industry matches the ICP | +20 |
| Company size matches the target | +15 |
| Business email passes validation | +10 |
| Website is present | +10 |
| Required ICP fields are missing | -10 |

Clamp the score to the configured range, such as 0 to 100.

These numbers are example defaults, not validated market benchmarks.

Store:

- Final score.
- Individual scoring rules applied.
- Reasons for positive and negative points.
- Scoring profile version.
- Timestamp.

Use transparent scoring rules so interviewers can inspect why a lead received its score.

## 9.3 AI qualification

The AI qualification service should return structured information such as:

```json
{
  "fit_category": "qualified",
  "confidence": 0.82,
  "reasoning_summary": "The company matches the target industry and size.",
  "missing_information": [
    "Annual revenue"
  ],
  "recommended_next_step": "Review the lead before outreach."
}
```

Validate the actual response schema. Treat confidence as a model-reported estimate, not a calibrated probability of conversion.

The service must distinguish verified input facts from missing or inferred information.

Do not allow the model to invent company facts or treat external instructions as trusted system instructions.

## 9.4 Message generation

Generate an outreach draft from:

- Verified lead fields.
- User-approved company information.
- Approved value proposition.
- Message template.
- Channel constraints.
- Tone and length requirements.

Store the generated draft and prompt version. Mark it as pending approval.

The user must be able to edit, approve, or reject the draft.

## 9.5 AI failure handling

Handle:

- Provider timeout.
- Rate-limit response.
- Invalid structured output.
- Empty response.
- Provider outage.
- Unexpected token usage.
- Content policy rejection.

AI failure must not corrupt the lead record or mark an incomplete workflow as successful.

Use deterministic fallback behavior where appropriate, such as retaining the lead and recording the AI step as failed.

---

# 10. API Specification

Use a versioned API prefix:

`/api/v1`

Publish OpenAPI documentation through FastAPI.

All organization-owned endpoints must verify membership and permissions. Use pagination for collection endpoints.

## 10.1 Authentication and organization

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/users/me` | Current user |
| GET | `/organizations` | Accessible organizations |
| GET | `/organizations/{organization_id}/members` | List members |
| POST | `/organizations/{organization_id}/members` | Invite a member |
| PATCH | `/organizations/{organization_id}/members/{member_id}` | Update membership |

Authentication callbacks and token handling depend on the selected identity provider.

## 10.2 Workflows

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/workflows` | List workflows |
| POST | `/workflows` | Create workflow |
| GET | `/workflows/{workflow_id}` | Get workflow |
| PATCH | `/workflows/{workflow_id}` | Update draft metadata |
| POST | `/workflows/{workflow_id}/validate` | Validate graph |
| POST | `/workflows/{workflow_id}/publish` | Publish version |
| POST | `/workflows/{workflow_id}/pause` | Pause triggers |
| POST | `/workflows/{workflow_id}/resume` | Resume triggers |
| POST | `/workflows/{workflow_id}/test-runs` | Execute test run |
| GET | `/workflows/{workflow_id}/versions` | List versions |
| GET | `/workflows/{workflow_id}/executions` | List executions |

Use explicit versioning and authorization checks for all workflow state transitions.

## 10.3 Leads

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/leads` | Search and list leads |
| POST | `/leads` | Create lead |
| GET | `/leads/{lead_id}` | Get lead |
| PATCH | `/leads/{lead_id}` | Update lead |
| POST | `/leads/imports` | Start CSV import |
| GET | `/leads/imports/{import_id}` | Get import status |
| GET | `/leads/imports/{import_id}/errors` | Get row errors |
| POST | `/leads/{lead_id}/score` | Recalculate score |
| POST | `/leads/{lead_id}/drafts` | Generate outreach draft |

Use multipart upload for CSV imports, with server-side file validation.

## 10.4 Executions

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/executions` | List executions |
| GET | `/executions/{execution_id}` | Get execution |
| GET | `/executions/{execution_id}/steps` | Get step history |
| POST | `/executions/{execution_id}/retry` | Retry eligible execution |
| POST | `/executions/{execution_id}/cancel` | Request cancellation |

Retries must respect idempotency and side-effect constraints.

## 10.5 Approvals

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/approvals` | List pending approvals |
| GET | `/approvals/{approval_id}` | Get approval details |
| POST | `/approvals/{approval_id}/approve` | Approve action |
| POST | `/approvals/{approval_id}/reject` | Reject action |

The server must derive the acting user from authenticated context, not from a user ID supplied in the request body.

## 10.6 Integrations

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/integrations` | List integrations |
| POST | `/integrations` | Create integration |
| GET | `/integrations/{integration_id}` | Get integration |
| POST | `/integrations/{integration_id}/test` | Test connection |
| PATCH | `/integrations/{integration_id}` | Update configuration |
| DELETE | `/integrations/{integration_id}` | Disable or remove connection |

Use a deletion or deactivation policy that preserves required historical records.

## 10.7 Webhooks and health

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/webhooks/inbound/{integration_id}` | Receive provider event |
| GET | `/webhook-deliveries` | List delivery attempts |
| POST | `/webhook-deliveries/{delivery_id}/retry` | Retry eligible delivery |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Dependency readiness |

Do not expose internal infrastructure details through public health responses.

## 10.8 API standards

Use:

- Correct HTTP status codes.
- Pydantic request and response models.
- Consistent error formats.
- Request correlation IDs.
- Pagination.
- Explicit timezone-aware timestamps.
- Rate limits on sensitive and expensive operations.
- Idempotency keys for suitable write operations.
- Clear API documentation.

Example error response:

```json
{
  "error": {
    "code": "WORKFLOW_VALIDATION_FAILED",
    "message": "The workflow contains invalid node configuration.",
    "request_id": "example-request-id",
    "details": []
  }
}
```

Do not expose raw stack traces or secrets to API consumers.

---

# 11. Frontend Product Requirements

Build a responsive web application with a consistent design system.

## 11.1 Navigation

Required navigation:

- Overview.
- Workflows.
- Leads.
- Executions.
- Approvals.
- Integrations.
- Team and settings.

## 11.2 Overview dashboard

Display:

- Total leads.
- Active workflows.
- Executions over time.
- Successful execution rate.
- Failed execution count.
- Pending approvals.
- Recent workflow activity.
- Recent failures.

All metrics must come from actual API data. Do not present hardcoded demo numbers as live metrics.

## 11.3 Workflows page

Display:

- Workflow name.
- Status.
- Last execution.
- Execution count.
- Success and failure information.
- Created and updated timestamps.

Actions:

- Create.
- Edit draft.
- Duplicate.
- Publish.
- Pause.
- Resume.
- Archive.

## 11.4 Workflow editor

Display:

- Node palette.
- Workflow canvas.
- Node configuration panel.
- Validation panel.
- Save status.
- Publish action.
- Test execution.
- Execution result link.

Use React Flow for node movement, edge creation, and selection. Persist graph changes through the API.

## 11.5 Leads page

Display:

- Search and filters.
- Lead table.
- Score and qualification status.
- Import action.
- Import history.
- Lead details.
- Qualification reasons.
- Outreach drafts and approval state.

## 11.6 Execution detail page

Display the execution timeline, step results, retry attempts, logs, and error information.

Actions must depend on the execution state and the current user's permissions.

## 11.7 Approval inbox

Display:

- Requested action.
- Lead or related resource.
- Draft content.
- Requesting workflow.
- Relevant context.
- Approve and reject actions.
- Decision history.

Require confirmation for consequential actions.

## 11.8 Integrations page

Display:

- Provider name.
- Connection status.
- Last successful test.
- Non-secret configuration.
- Test connection action.
- Disable or reconnect action.

Never render stored credentials back into the UI.

## 11.9 UX states

Every data-driven page must support:

- Loading state.
- Empty state.
- Error state.
- Retry action where appropriate.
- Permission-denied state.
- Success feedback.
- Responsive layouts.
- Keyboard-accessible controls.

---

# 12. Security Requirements

Security is part of the implementation, not a final cosmetic task.

## 12.1 Authentication and authorization

- Use a maintained authentication mechanism.
- Enforce organization membership in the backend.
- Check role permissions on every protected action.
- Prevent insecure direct object references.
- Test cross-organization data isolation.
- Protect account and session lifecycle operations.

## 12.2 Secrets

- Keep secrets in environment variables or a suitable secret manager.
- Commit only `.env.example`.
- Rotate exposed credentials.
- Redact secrets from logs.
- Encrypt sensitive integration credentials at rest where stored.
- Restrict access to credentials by integration adapter.
- Never send secret values to the browser.

## 12.3 API and webhook protection

- Validate request payloads.
- Apply rate limits.
- Enforce request-size limits.
- Verify webhook signatures when supported.
- Reject expired or replayed signed events where the protocol permits.
- Deduplicate event processing.
- Apply request timeouts.
- Restrict outbound destinations.

## 12.4 Server-side request forgery protection

Workflow URLs and webhook destinations must not permit requests to arbitrary internal infrastructure.

- Block loopback and private network destinations unless explicitly authorized.
- Validate resolved IP addresses.
- Revalidate destinations after redirects.
- Restrict outbound protocols.
- Apply network-level egress rules where available.

## 12.5 AI security

- Treat lead data and external content as untrusted.
- Separate system instructions from user-provided content.
- Validate model outputs.
- Restrict tool permissions.
- Require approval for consequential actions.
- Avoid autonomous execution of arbitrary generated code.
- Record the provenance of generated content.
- Minimize data sent to external model providers.

## 12.6 Data protection

- Define data retention rules.
- Avoid logging full personal records unnecessarily.
- Use secure file storage for imports.
- Remove temporary files after processing.
- Restrict access to export files.
- Provide deletion or deactivation policies.
- Back up PostgreSQL and test recovery.

---

# 13. Testing Strategy

Use multiple levels of testing.

## 13.1 Unit tests

Test:

- Lead normalization.
- Email validation.
- Duplicate detection.
- Lead scoring rules.
- Workflow graph validation.
- Node configuration validation.
- Permission checks.
- Retry eligibility.
- Idempotency logic.
- AI response validation.
- Error classification.

Use mocks for external services.

## 13.2 Integration tests

Test:

- FastAPI endpoints with a test database.
- Database migrations.
- Redis and Celery integration.
- Workflow execution and state transitions.
- Approval creation and resumption.
- Webhook signature validation.
- External API error handling.
- Organization isolation.
- Transactional job dispatch.

Use real PostgreSQL and Redis test instances where practical. SQLite is not a complete substitute for PostgreSQL behavior.

## 13.3 End-to-end tests

Use Playwright to test:

1. User signs in.
2. User creates a workflow.
3. User validates and publishes it.
4. User imports leads.
5. Workflow processes a lead.
6. AI produces a draft.
7. The draft appears in approvals.
8. User approves the draft.
9. The configured integration executes.
10. The execution page displays the result.

Also test rejection, failure, retry, invalid CSV, and unauthorized access.

## 13.4 CI quality gates

Every pull request should run:

- Python linting.
- Python type checks.
- Frontend linting.
- TypeScript checks.
- Unit tests.
- Integration tests where practical.
- Build validation.
- Dependency or security checks.

Block merging when required checks fail.

## 13.5 Initial acceptance targets

These are engineering targets, not existing product results.

- All critical workflow transitions have automated tests.
- No known cross-organization data access.
- Duplicate event delivery does not create duplicate protected side effects when the integration supports idempotency.
- Transient failures follow the configured retry policy.
- Invalid workflow definitions cannot be published.
- Approval is required before protected external sends.
- API documentation matches implemented routes.
- A clean environment can run the application using documented setup instructions.

Do not advertise test coverage or performance numbers until you have measured them.

---

# 14. DevOps and Deployment

## 14.1 Local development

Use Docker Compose to start:

- PostgreSQL.
- Redis.
- FastAPI API.
- Celery worker.
- Celery scheduler if required.
- Next.js frontend.

Use separate commands or profiles for optional services.

The project must start from documented commands on a fresh developer machine.

## 14.2 Environment configuration

Create `.env.example` with variable names and safe placeholder values.

Example categories:

```dotenv
APP_ENV=development
API_PORT=8000
WEB_PORT=3000

DATABASE_URL=
REDIS_URL=

AUTH_SECRET=
AI_PROVIDER_API_KEY=

EMAIL_PROVIDER_API_KEY=
EMAIL_FROM_ADDRESS=

CREDENTIAL_ENCRYPTION_KEY=
SENTRY_DSN=
```

Adapt the final variables to the actual authentication and integration implementations.

Do not put real credentials in this file.

## 14.3 Database migrations

Use Alembic.

Requirements:

- Create migrations for schema changes.
- Run migrations in a controlled deployment step.
- Test migrations against PostgreSQL.
- Document rollback or forward-fix procedures.
- Avoid destructive production migrations without a recovery plan.

## 14.4 Continuous integration

Create GitHub Actions workflows for:

- Pull request checks.
- Python tests and linting.
- Frontend checks.
- Production build.
- Dependency security checks.

Use protected branches and required checks.

## 14.5 Continuous deployment

A deployment pipeline should:

1. Run required checks.
2. Build versioned artifacts or container images.
3. Apply approved database migrations.
4. Deploy the frontend and API.
5. Deploy background workers.
6. Verify readiness endpoints.
7. Run smoke tests.
8. Report deployment success or failure.

Use separate development and production environments.

## 14.6 Monitoring

Track:

- API latency.
- HTTP error rates.
- Worker health.
- Queue backlog.
- Workflow success and failure rates.
- Retry counts.
- AI provider errors.
- Integration delivery failures.
- Database connectivity.
- Resource consumption.

Use correlation IDs to connect API requests, jobs, execution steps, and integration calls.

## 14.7 Backup and recovery

Document:

- PostgreSQL backup frequency.
- Backup retention.
- Restore procedure.
- Recovery objectives.
- Handling of pending jobs after restoration.
- Credential rotation after incidents where needed.

Test restoration at least once before claiming the recovery process works.

---

# 15. Non-Functional Requirements

## Performance

Initial design targets:

- Typical API reads should aim for a p95 latency below 500 ms under a defined test load, excluding external provider calls.
- Workflow execution should occur asynchronously.
- Large CSV imports should not block request handlers.
- Collection endpoints should use pagination.
- Dashboard queries should use appropriate indexes.

Measure performance before claiming these targets have been achieved.

## Reliability

- Persist execution state.
- Retry eligible transient failures.
- Handle duplicate events.
- Isolate failing integrations.
- Recover jobs after worker restarts.
- Avoid silent job loss.
- Provide actionable error information.

## Scalability

- Keep API instances stateless where possible.
- Allow workers to scale independently.
- Use database indexes and query analysis.
- Apply queue backpressure and rate limits.
- Introduce more complex distributed architecture only when needed.

## Maintainability

- Use type hints.
- Keep business logic outside route handlers.
- Define interfaces for integrations.
- Document architectural decisions.
- Enforce linting and testing.
- Keep workflow node types explicit and versioned.

## Accessibility

- Support keyboard navigation.
- Provide labels for form controls.
- Maintain visible focus states.
- Use adequate contrast.
- Do not communicate status through color alone.

---

# 16. Four-Week Implementation Roadmap

The roadmap assumes a focused MVP and daily implementation time. Adjust the schedule based on your experience and available hours.

## Week 1: Foundation and core application

### Tasks

1. Initialize the monorepo.
2. Configure Next.js and FastAPI.
3. Start PostgreSQL and Redis with Docker Compose.
4. Configure SQLAlchemy and Alembic.
5. Implement authentication.
6. Create organizations and membership roles.
7. Create lead models and endpoints.
8. Build the application layout and navigation.
9. Build the leads table and detail view.
10. Add basic API and database tests.

### Deliverable

A deployed or locally runnable application with authentication, organization isolation, and working lead management.

### Completion criteria

- Users sign in.
- Protected APIs enforce access.
- Leads persist in PostgreSQL.
- Unauthorized organization access is rejected.
- Database migrations work from a clean database.

## Week 2: Workflow builder and execution engine

### Tasks

1. Define the workflow JSON schema.
2. Build the backend node registry.
3. Implement graph validation.
4. Build the React Flow editor.
5. Implement workflow draft saving.
6. Implement immutable published versions.
7. Add manual execution triggers.
8. Configure Celery workers.
9. Implement execution and step records.
10. Add retries and idempotency protections.

### Deliverable

A user creates and publishes a workflow, runs it, and inspects persisted execution history.

### Completion criteria

- Invalid workflows cannot be published.
- Background tasks run independently of browser sessions.
- Step results are persisted.
- Eligible failures follow the retry policy.
- Duplicate job delivery is handled safely.

## Week 3: AI, leads, integrations, and approvals

### Tasks

1. Implement CSV import.
2. Add duplicate detection.
3. Implement rule-based lead scoring.
4. Integrate one LLM provider.
5. Validate structured AI output.
6. Generate personalized drafts.
7. Add approval requests.
8. Add approval and rejection endpoints.
9. Integrate one email or CRM provider.
10. Implement incoming webhook validation and deduplication.

### Deliverable

A complete lead workflow with AI-assisted qualification, approval, integration execution, and error handling.

### Completion criteria

- Leads import successfully.
- Duplicate handling follows the documented policy.
- AI failures do not corrupt lead data.
- No protected external message is sent before approval.
- Integration results appear in execution history.

## Week 4: Production readiness and portfolio presentation

### Tasks

1. Add missing unit and integration tests.
2. Add Playwright end-to-end tests.
3. Configure GitHub Actions.
4. Finalize Dockerfiles and Docker Compose.
5. Deploy the frontend, API, and workers.
6. Configure production secrets.
7. Add structured logs and health checks.
8. Verify backup and recovery instructions.
9. Write the architecture and API documentation.
10. Record a demonstration video.

### Deliverable

A deployed, documented, tested project with a complete end-to-end demonstration.

### Completion criteria

- A fresh setup follows the README successfully.
- Required CI checks pass.
- Production endpoints are healthy.
- Background workers process jobs.
- The complete demo workflow works.
- No production secrets appear in source control.

---

# 17. Required Demonstration Scenario

Build one polished end-to-end scenario rather than many incomplete features.

## Scenario: Automated B2B lead qualification

### Step 1: Create a workflow

The user creates a workflow:

New Lead → Validate Data → Detect Duplicate → Score Lead → Check Score → Generate Draft → Request Approval → Send Email → Record Result.

### Step 2: Import sample leads

Upload a CSV containing sample companies, job titles, work emails, industries, and websites.

Include some invalid and duplicate rows to demonstrate validation.

Use fictional sample data or data you have permission to process.

### Step 3: Execute the workflow

The system creates an execution record and queues the work.

The worker validates the lead, applies scoring rules, and evaluates the configured conditions.

### Step 4: Generate an AI draft

The AI service creates a message using verified input fields and the approved value proposition.

The application validates and stores the draft.

### Step 5: Pause for approval

The workflow enters waiting_for_approval.

The dashboard shows the draft and its relevant context.

### Step 6: Approve the action

The authorized user approves the draft.

The worker resumes from its persisted checkpoint.

### Step 7: Execute the integration

The email adapter sends the approved message using the configured provider.

For local development, a mock email adapter should record the intended send without contacting an external recipient.

### Step 8: Inspect execution results

The execution detail page shows:

- Successful steps.
- Failed steps, if any.
- Retry attempts.
- AI output.
- Approval decision.
- Integration response summary.
- Total execution duration.

### Step 9: Demonstrate failure recovery

Simulate a transient provider failure.

Show the retry process, persisted error details, and eventual success or controlled failure.

This scenario demonstrates full-stack development, Python backend logic, asynchronous processing, AI integration, database persistence, security, and operational reliability.

---

# 18. GitHub and Portfolio Deliverables

The repository must contain:

- README.md.
- PRD.md.
- SRS.md.
- TRD.md.
- ARCHITECTURE.md.
- API.md.
- DATABASE.md.
- SECURITY.md.
- TESTING.md.
- DEPLOYMENT.md.
- RUNBOOK.md.
- Architecture diagram.
- Database ER diagram.
- Workflow graph example.
- OpenAPI documentation.
- `.env.example`.
- Docker Compose configuration.
- GitHub Actions workflows.
- Automated tests.
- Seed data.
- Screenshots.
- Demo video link.
- Known limitations and future roadmap.

## README structure

1. Project overview.
2. Problem statement.
3. Features.
4. Technology stack.
5. Architecture diagram.
6. Screenshots.
7. Live demo.
8. Local setup.
9. Environment variables.
10. Database migrations.
11. Running workers.
12. Running tests.
13. API documentation.
14. Security model.
15. Deployment.
16. Known limitations.
17. Future improvements.

Do not publish credentials, customer information, proprietary employer code, or private company configuration.

---

# 19. Interview Preparation

Be prepared to explain these design decisions.

## Python and backend

- Why FastAPI?
- How does Pydantic validate data?
- How do you structure service and repository layers?
- How do database transactions work?
- How do you handle concurrent requests?
- How do you distinguish validation failures from transient failures?

## Workflow engine

- How do you validate a workflow graph?
- How do you execute nodes in dependency order?
- How do you persist execution checkpoints?
- How do you resume an approval-paused workflow?
- How do you prevent duplicate side effects?
- How do you handle worker restarts?

## AI

- How do you validate structured model output?
- How do you reduce hallucinations?
- How do you handle provider timeouts?
- Why should AI not control authorization?
- How do you prevent prompt injection from imported data?
- How do you track prompt versions and AI usage?

## Database and distributed systems

- Why PostgreSQL?
- Why Redis and Celery?
- What happens if the database commits but queue publication fails?
- How do you handle duplicate webhook delivery?
- What are the trade-offs of at-least-once processing?
- How would you investigate slow queries?

## Full-stack development

- How does the frontend persist workflow graph changes?
- How do you handle loading and error states?
- How do you prevent stale execution data?
- How do you enforce permissions on the server?
- How do you test the complete user journey?

## DevOps

- How does CI differ from CD?
- How do you manage environment-specific secrets?
- How do you deploy database migrations safely?
- How do you monitor background workers?
- How do you restore a database backup?
- How do you roll back a bad release?

Answer using implementation details from your own code. Do not memorize generic definitions without understanding your actual design.

---

# 20. Out of Scope for Version 1

Avoid these until the required end-to-end workflow works:

- Arbitrary user-written code execution.
- A general-purpose workflow scripting language.
- Kubernetes.
- Multi-region deployment.
- Complex microservice architecture.
- An unrestricted marketplace of integrations.
- Autonomous sending of large outreach campaigns.
- Multi-agent orchestration.
- Advanced billing and subscription management.
- Custom machine-learning model training.
- Unlimited workflow loops and branching complexity.

These features add complexity without improving the initial demonstration enough to justify the time.

---

# 21. Final Definition of Done

FlowOps AI Version 1 is complete when:

1. A user can sign in and work inside an authorized organization.
2. A user can create, validate, publish, and execute a workflow.
3. Workflow definitions have immutable published versions.
4. A user can import leads and inspect validation results.
5. Lead scoring produces transparent, reproducible results.
6. AI generates validated follow-up drafts.
7. Approval is required before protected external sends.
8. Background workers execute and persist workflow state.
9. Eligible transient failures follow the retry policy.
10. Duplicate event delivery does not produce duplicate protected side effects where idempotency is supported.
11. Incoming and outgoing integrations have appropriate security and delivery records.
12. Execution history displays step-level results.
13. Organization access and role permissions have automated tests.
14. Docker-based local development works.
15. CI checks run automatically.
16. The application and workers are deployed and monitored.
17. API, architecture, security, and setup documentation is complete.
18. A recorded demonstration shows the full lead qualification workflow.

# 22. Build Instructions for the AI Coding Assistant

Use this section as the project-level instruction when working with an AI coding assistant.

## Role

Act as a senior full-stack software engineer, Python backend engineer, workflow automation architect, database engineer, test engineer, and DevOps engineer.

Build FlowOps AI according to this document.

## Mandatory development rules

1. Read the relevant requirements and architecture before implementing a module.
2. Inspect the existing repository before changing files.
3. Create a short implementation plan for each milestone.
4. Implement real database models, API endpoints, business logic, and frontend interactions.
5. Do not substitute mock data for required production functionality.
6. Use mocks only for tests, explicit demo mode, and development fallbacks.
7. Keep secrets out of source control.
8. Validate data on the backend.
9. Enforce organization isolation and authorization on the backend.
10. Add migrations when database schemas change.
11. Add automated tests for important business logic and state transitions.
12. Run relevant tests and quality checks after changes.
13. Fix regressions before moving to the next milestone.
14. Document environment variables and setup commands.
15. Record significant architectural decisions.
16. Report what was implemented, what was tested, and what remains incomplete.
17. Do not claim that an integration, test, or deployment works unless it has been verified.
18. Never execute arbitrary generated Python code from a workflow.
19. Never bypass approval requirements for protected external actions.
20. Do not implement future roadmap features before the current milestone passes its acceptance criteria.

## Required implementation sequence

Milestone 1: Repository, development environment, database, authentication, organizations, and leads.

Milestone 2: Workflow schema, node registry, graph validation, visual editor, and versioning.

Milestone 3: Background execution engine, persisted state, retries, idempotency, and logs.

Milestone 4: CSV imports, deterministic scoring, AI qualification, message drafts, and approval gates.

Milestone 5: External integrations, inbound and outbound webhooks, delivery tracking, and error recovery.

Milestone 6: Security review, test automation, CI/CD, deployment, monitoring, documentation, and demo.

Do not proceed to the next milestone until the current milestone meets its acceptance criteria.

## Expected result

Deliver a working, maintainable, documented, and deployed full-stack application. Every major feature must connect to the backend and database. Every automation must produce inspectable execution records. External side effects must follow authorization, approval, retry, and idempotency rules.

The final product must demonstrate that the developer understands Python, APIs, frontend development, relational databases, asynchronous processing, AI integration, system reliability, testing, security, and deployment.

---

END OF TECHNICAL SPECIFICATION
