# Security model

FastAPI Users owns authentication and Argon2 password hashing. Database sessions expire after one hour; logout removes the active token. Cookies are HttpOnly, SameSite=Lax and Secure when APP_ENV is production. Use HTTPS and the exact WEB_ORIGIN for production.

Every tenant route checks membership and every mutation checks the required role. Owner/admin manages membership; only the owner grants admin. Owner access cannot be removed through the role-change endpoint. Member writes leads; viewer reads. Audit access is owner/admin only. All SQLAlchemy queries bind parameters, and resource lookups include organization identifiers.

Request bodies are bounded to 1 MiB before parsing. A shared Redis limiter fails closed when unavailable. Untrusted Origin headers cannot bypass the configured origin. Submitted validation inputs, passwords and tokens are excluded from error responses and application logs. React escapes user-provided text; website values are validated HTTP(S) URLs.

Registration is open in this development release. Password reset, verification mail, account removal, session cleanup scheduling and production ingress configuration remain required before a public launch. The application does not currently contact AI, email or CRM providers. Do not store employer/customer production data in a development demo.

Archive is a business status change, not personal-data erasure. A production retention/deletion policy and backups must be configured before real data is retained. No automatic retention job is implemented yet.


Execution requests bind organization-scoped idempotency keys to a canonical request hash. Every run pins a published immutable graph, checks configured action permissions, and rechecks the initiating user's active account and current membership at each step. Automatic triggers use the published version's author as that principal. UUID-only Celery messages carry no lead details or credentials.

Approval decisions require owner/admin membership, a pending request, its current revision and payload hash, and an unexpired checkpoint. Generic approval cannot authorize email. Test runs simulate business writes. Unknown external outcomes block retries; no API provides a force-send bypass. Error summaries and frame-only failure details exclude exception values and locals; frames are limited to owners/admins. Worker errors log fixed codes, execution/request IDs and durations rather than SQL/provider payloads.
