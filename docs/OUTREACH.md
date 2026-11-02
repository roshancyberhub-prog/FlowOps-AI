# Structured drafts and protected mock email

The development setup explicitly selects `AI_PROVIDER=mock` and `EMAIL_PROVIDER=mock`. Python defaults both to `disabled` when not configured. **The current provider implementations make no live AI calls and send no external email.** Mock output and delivery receipts are labelled in the interface and carry simulated metadata. The source instructions authorize this fallback because no provider credentials are available. Connecting a live OpenAI provider requires a separate credential decision; no key was created or reused.

## Processing and stored evidence

A draft workflow qualifies provided lead fields and generates a subject/body through an async provider-neutral interface. The application validates raw qualification and draft content with strict Pydantic schemas. Outputs cannot specify recipients, permissions or approval. Unexpected fields, out-of-range confidence, empty content and subject control characters fail the node without saving a draft. The server binds the recipient to its lead snapshot.

The deterministic mock follows the recorded rule score for its demo fit category. Its 0.50 confidence is a simulated estimate, not a prediction or real model judgment. It uses supplied facts and a configured value proposition for a follow-up. Only `initial_follow_up` is supported. Provider/model, prompt versions, zero simulated token counts and provided facts are saved separately from generated qualification. Provided fields are not advertised as externally verified facts. Email is excluded from the provider fact input.

Draft generation stores one draft per execution/node. A later draft supersedes the previous current draft and removes prior email authority from execution context. Drafts retain their revision, recipient, content, metadata and execution. The request-approval node loads the stored current draft and binds its exact snapshot to a payload hash and approval revision.

## Review and send rules

Writers can edit the current unapproved draft while its execution is active. Editing locks execution before draft/approval, increments the draft revision, updates any pending email approval, increments that review's revision and recomputes its hash. Old review submissions return 409. The recipient cannot be edited through this route. Approved, superseded or terminal-run drafts cannot be changed.

Owners/admins approve or reject. Approval verifies the pending state, current hash/revision, unexpired request and exact stored draft. A generic continue checkpoint cannot authorize email. Rejection cancels the execution. A send also checks the current approving user's account/role, the exact approved snapshot, current stored recipient and provided lead facts in live mode. A changed recipient/facts or revoked approver blocks sending and requires a new reviewed run.

The mock email adapter derives a stable receipt ID from the execution/node idempotency key and performs no I/O. Receipts are unique per execution/node, link the approval/draft and record `status: simulated`, `simulated: true`, and `external_message_sent: false`. Test mode always forces mock email, even when email delivery is disabled. Live mode requires the configured mock adapter and applies preceding database changes normally. Completed earlier steps remain committed if a later node fails.

Interrupted external send intents and unclassified external exceptions are uncertain and cannot be retried automatically or manually. This conservative rule also applies to the send node in a mock workflow. There is no force-send or force-resend endpoint. No exactly-once delivery guarantee is made for future real providers.

## API and interface

| Method | Route under `/api/v1` | Behavior |
|---|---|---|
| GET | `/providers/status` | Non-secret provider modes; live-provider availability is false |
| GET | `/leads/{id}/draft-workflows` | Paginated active published draft workflows and role eligibility |
| POST | `/leads/{id}/drafts` | Queue a chosen published workflow; requires Idempotency-Key |
| GET | `/leads/{id}/drafts` | Paginated stored drafts |
| GET | `/drafts/{id}` | Draft, qualification, metadata and execution status |
| PATCH | `/drafts/{id}` | Writer update with expected_revision, subject and body |
| GET | `/deliveries` | Paginated organization receipts; optional execution_id/draft_id |

The generation request contains `workflow_id`, optional `workflow_version_id` and `mode: test|live`; generation occurs in the worker. Lead details list drafts and can start eligible published workflows. Draft detail shows qualification, provided fields, edit controls, approval/execution links and receipts. Approval cards show current content and mock/test labels. Execution details retain every step and receipt.

Milestone 4 acceptance passed run 40747693463: 82 backend tests and all five browser journeys. Tests cover stale-review invalidation, invalid/disabled output, viewer/cross-tenant denial, exact approved mock payloads, rejection, changed recipients/facts, revoked approvers and duplicate receipt prevention. The full browser flow imports fitting leads, edits and approves one draft, rejects the other, and verifies all nine worker steps plus a simulated receipt with no external email. Desktop/mobile and draft screenshots were reviewed from CI artifacts. Live AI/email remain unconfigured.
