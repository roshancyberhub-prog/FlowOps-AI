# Implemented API

OpenAPI is served at `/openapi.json`; interactive documentation is at `/docs`. Application routes use `/api/v1`.

Authentication uses the `flowops_session` HttpOnly cookie. Organization-owned routes require `X-Organization-ID` and verify that the authenticated user is a member. A caller outside the selected organization receives 403; an inaccessible resource inside a different organization receives 404. Viewer writes receive 403.

| Method | Route under `/api/v1` | Behavior |
|---|---|---|
| POST | `/auth/register` | Register account with email/password/display_name |
| POST | `/auth/session/login` | Form-encoded username/password; set session cookie |
| POST | `/auth/session/logout` | Revoke current token and clear cookie |
| GET | `/users/me` | Current user, excluding password hash |
| GET, POST | `/organizations` | List accessible workspaces; create owned workspace |
| GET, POST | `/organizations/{id}/members` | List members; add an existing account |
| PATCH | `/organizations/{id}/members/{member_id}` | Change permitted membership roles |
| GET, POST | `/leads` | Search/paginate or create workspace leads |
| GET, PATCH, DELETE | `/leads/{id}` | Inspect, edit, or archive a lead |
| GET | `/audit` | Owner/admin event history, 50 rows per page |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | PostgreSQL and Redis readiness |

Lead listing accepts `search`, `status`, `page` (starting at 1), and `page_size` (1–100). Omitting status excludes archived leads. Responses contain `items`, `total`, `page`, and `page_size`. Scores and organization identifiers are not writable through lead inputs.

Errors contain an `error` object with `code`, `message`, `request_id`, and `details`. Validation responses omit raw submitted inputs. Every response carries `X-Request-ID`. Health routes do not reveal infrastructure errors. CSRF protection rejects browser mutations from an origin other than `WEB_ORIGIN`.


## Workflow definitions

`GET/POST /workflows` lists paginated workflows or creates a draft. `GET/PATCH /workflows/{id}` reads or saves it; writes include `expected_revision` to reject stale edits. `POST /workflows/{id}/validate` validates the stored graph, or a supplied unsaved graph, without executing it. `POST /workflows/{id}/publish` validates and freezes a new version transactionally. `/pause`, `/resume`, `/archive` and `/duplicate` implement the corresponding transitions. `GET /workflows/{id}/versions` is paginated; `/versions/{version_id}` reads an immutable snapshot. `/workflows/node-types` and `/workflows/templates` expose the bounded registry and starter templates.

Graph schema version 1 permits one trigger, one edge per output and branches without joins or cycles. Node configuration and action permissions are validated on publication. Every email path must include a generated draft followed by a fresh approval node. A later draft invalidates the earlier approval path. The worker enforces the pinned definition and current user permissions during execution.

## Workflow execution

| Method | Route | Behavior |
|---|---|---|
| POST | `/workflows/{id}/test-runs` | Queue published version in test mode |
| POST | `/workflows/{id}/runs` | Queue published version in live mode |
| GET | `/executions` | Paginated organization runs; optional status/workflow_id |
| GET | `/executions/{id}` | Pinned version, status, context and failure summary |
| GET | `/executions/{id}/steps` | Attempt history, 100 per page; frames restricted to owner/admin |
| POST | `/executions/{id}/cancel` | Cooperative cancellation; completed effects remain |
| POST | `/executions/{id}/retry` | Retry an eligible failed node, at most five manual retries |
| GET | `/approvals` | Paginated requests, optional status |
| GET | `/approvals/{id}` | Current request and review payload |
| POST | `/approvals/{id}/approve` | Owner/admin approval with current revision and payload_hash |
| POST | `/approvals/{id}/reject` | Owner/admin rejection; cancel the waiting run |
| GET | `/execution-health` | Authenticated dispatch heartbeat, without host details |

Run requests require `Idempotency-Key` (1–200 alphanumeric/colon/underscore/hyphen characters). JSON accepts optional `workflow_version_id` and either `lead_id` or `sample_lead`. The version must belong to this workflow and a stored lead must belong to this organization. New requests return 202; identical replay returns 200; conflicting replay returns 409. Viewers cannot request, retry or cancel runs.

Test mode records execution and approval history while simulating lead status changes and internal notifications. Live mode applies those database changes. AI and send nodes currently fail explicitly as unconfigured. Score nodes use the immutable profile pinned at publication. Manual execution can exercise any published trigger definition; automatic lead-created and interval triggers run the active published version in live mode. Inbound webhook dispatch is not implemented yet.

Generic checkpoints use `kind: continue`; email checkpoints default to `kind: email` and require a preceding draft. The decision body contains `revision`, `payload_hash` and an optional comment up to 1000 characters. Stale, completed or expired reviews return 409. Unknown external outcomes cannot be manually or automatically retried.


## Lead operations

See [scoring routes and profile semantics](SCORING.md) and [CSV upload, history and report routes](IMPORTS.md). Scoring is deterministic; CSV processing runs through durable Celery batches. AI generation and email delivery remain unconfigured.
