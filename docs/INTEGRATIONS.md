# Integrations and webhooks

Owners and admins create, test, enable and disable connections in **Integrations**. Members and viewers may inspect connection status and event/delivery history in their own workspace. Settings are fixed on creation; disable and replace a connection when changing its target. Disabled connections reject new ingress and queued outgoing work is checked again before delivery. An already started network request cannot be recalled.

## Public GitHub repository

Choose **GitHub · public repository**, enter the owner and repository, then select **Test connection**. This calls the real, fixed `api.github.com/repos/{owner}/{repo}` endpoint with a 10-second timeout. No credential is needed for public metadata. Private repositories are unsupported. Only repository name, description, star/fork/issue counts and default branch are stored; extra provider fields are discarded. Errors are safe codes (`NOT_FOUND`, `RATE_LIMITED`, `PROVIDER_UNAVAILABLE`); prior successful metadata is cleared on a failed retest. Tests are throttled to one per connection per 30 seconds.

Reference: https://docs.github.com/en/rest/repos/repos#get-a-repository . Unit tests use HTTPX MockTransport; CI separately performs a real read-only request to `octocat/Hello-World`. Local direct network access in the coding workspace was unavailable; only a successful CI smoke check verifies the live adapter.

## Signing configuration

Run `python3 scripts/setup-env.py` for a new local setup. It creates private `.env` settings with a random database password and a random 256-bit `WEBHOOK_SIGNING_KEY`; existing files, including symlinks, are left unchanged. Never commit `.env`. Existing installations must independently generate a strong random signing key and set the same value on the API and workers. An empty key disables signed ingress and outgoing delivery. No secret is returned by any API or frontend.

Sender/receiver operators must arrange a shared **endpoint key** through a secure channel. Derive it with standard HMAC-SHA256:

```python
endpoint_key = hmac.digest(master_key.encode(), integration_id.encode(), "sha256")
message = str(timestamp).encode() + b"." + raw_body
signature = "sha256=" + hmac.new(endpoint_key, message, hashlib.sha256).hexdigest()
```

The master key stays on the FlowOps server; provision only the derived key to the sender/receiver. Use the canonical lower-case integration UUID. Rotating the master invalidates all endpoint keys, so coordinate reprovisioning. Send headers `X-FlowOps-Timestamp` (Unix seconds) and `X-FlowOps-Signature`. The exact bytes of the body are signed. A sender with a provisioned endpoint key uses the second and third lines above; it must not derive the key again. Keep clocks synchronized; ingress accepts at most five minutes of skew.

## Incoming lead events

POST to `/api/v1/webhooks/{integration_id}` (no session cookie required):

```json
{"event_id":"crm:lead:001","lead":{"name":"Fictional Buyer","email":"buyer@example.com","company":"Example Co"}}
```

The 64 KiB body cap, normal API rate limits and signature verification apply. Event IDs (1–100 letters, digits, `:`, `_`, `-`) deduplicate per integration. Exact repeated bytes return the existing event with `duplicate: true`; the same ID with different bytes returns 409. Event IDs remain retained indefinitely, even when the signing window has passed, to prevent later replay with a fresh signature. Event history stores body hashes and record IDs, not a second copy of the raw lead payload.

The event inserts a validated lead or reuses an existing email in that workspace without overwriting it. Archived leads are rejected. New leads also trigger active Lead Created workflows. An optional linked workflow must be active with a published Webhook trigger. Its execution and the event are committed together. Invalid/misconfigured workflow events roll back the whole transaction. Every action still checks the publishing user's current permission. Receiving a webhook never grants authority to approve an email.

## Outgoing operational events

Set `WEBHOOK_ALLOWED_HOSTS` to exact, comma-separated destination hostnames; empty blocks all outgoing destinations. Only public HTTPS on port 443 is supported. Credentials, queries, fragments, redirects and proxy environment settings are blocked. All DNS answers must be public. Each request connects to a checked IP while retaining the original Host and TLS SNI to prevent DNS rebinding. HTTPX transport extension reference: https://www.python-httpx.org/advanced/extensions/ . Enforce an independent egress firewall as another layer in production.

An explicit owner/admin action **Send operational test event** queues an `integration.test` envelope. The API also accepts `execution_id` in `POST /integrations/{id}/deliveries` for an organization-scoped `execution.status` snapshot. Require `Idempotency-Key` (8–200 characters). Reusing a key returns the same delivery; differing input returns 409. Envelopes contain only event/workspace/execution IDs and status, not lead contact data or message contents. The stable delivery UUID is both `Idempotency-Key` and `X-FlowOps-Event-ID` at the receiver. Body bytes remain stable across attempts; timestamps/signatures are fresh.

Celery Beat dispatches due deliveries every five seconds. Each request has a committed attempt intent, a 45-second lease, a 10-second network timeout and at most five attempts, with 5/10/20/40-second backoff. Receivers must deduplicate by event UUID and atomically persist that UUID with their side effect. Enable **receiver guarantees deduplication** only when that contract is implemented. With that contract, network uncertainty, HTTP 429 and 5xx retry automatically; other statuses are terminal. Without it, an unknown outcome becomes `uncertain` for operator investigation; even known HTTP failures do not automatically retry. A lost worker's in-flight attempt is also uncertain. Never create a new event as a blind retry of an uncertain side effect. Delivery guarantees are at least once when retries are enabled, not exactly once.

The requesting account, current workspace role and enabled integration are rechecked before each attempt. Delivery history exposes attempt number, status, safe error code, HTTP status and uncertainty. Response bodies, authorization headers and signing keys are never stored. Limits: 100 integrations/workspace, 100 pending deliveries/workspace, latest 50 ingress and outgoing records in the UI.
