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

Graph schema version 1 permits one trigger, one edge per output and branches without joins or cycles. Node configuration and action permissions are validated on publication. Every email path must include a generated draft followed by a fresh approval node. A later draft invalidates the earlier approval path. These are definition constraints; execution is the next milestone.
