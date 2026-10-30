# Retention and deletion

Use fictional data for this portfolio release. Archiving a lead changes its business status; it is not erasure. Do not silently change retention periods when deploying a new version.

| Data | Current retention and cleanup |
|---|---|
| Raw CSV upload bytes | Cleared on success/terminal failure; abandoned active uploads expire after 7 days, in batches of 100 |
| Expired session tokens | Unusable after the configured lifetime (default 1 hour); worker maintenance removes up to 1000 expired rows every 5 minutes |
| Active session tokens | Retained until expiry or revoked immediately by logout |
| Lead records and CSV row reports | Retained in their workspace until an explicitly authorized deletion/anonymization operation; archive retains the record and email uniqueness |
| Workflow versions, scores, execution/step/approval/draft/receipt history | Retained as workspace evidence; published definitions and scoring profiles remain immutable |
| Webhook event IDs/body hashes and delivery idempotency keys | Retained with their integration to preserve deduplication, including retries signed with a fresh timestamp |
| Application logs | Operator target: 14 days, restricted access; exclude bodies, query values, credentials and email content |
| Backups | Operator target: 7 daily + 4 weekly encrypted off-host copies; expire them consistently with an approved erasure request |

Database business-history purging and self-service account/workspace erasure are not implemented. For authorized erasure, the operator must define a reviewed, organization-scoped migration covering lead contact fields, import row values, execution contexts/input/output summaries, AI draft/qualification/fact snapshots, approval payloads, receipts, notifications, account identity, logs and backup expiry. A lead-only delete is insufficient. Check foreign keys and immutable history constraints; preserve opaque tombstones/hashes needed to prevent replay rather than erasing deduplication keys blindly. Stop affected jobs, take a controlled backup, rehearse against a disposable restore, verify other workspaces are unchanged, and audit the operation before resuming work.

Do not retain real customer data under this indefinite business-history policy without agreeing on concrete periods and implementing the required erasure workflow first. Upload/session cleanup is automated and tested; broader deletion requires explicit operator authorization and is not advertised as available in the UI.
