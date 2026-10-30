# Software requirements and acceptance

Normative requirements are in [REQUIREMENTS.md](REQUIREMENTS.md); verified release state is in [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).

| Requirement | Implemented behavior | Verification |
|---|---|---|
| Authentication and organization isolation | Maintained password/session handling, revocation, four roles, scoped resources | Backend tenant/role/session tests; browser signup/logout and viewer denial |
| Visual workflows | React Flow, bounded graph validation, revision locks, immutable publication, templates | Graph/API tests and browser save/publish/version journey |
| Reliable execution | Celery + durable outbox/state, leases, finite retries, approvals, delays, cancellation | PostgreSQL concurrency/recovery tests and separate Docker workers |
| Lead operations | Bounded CSV reports, normalized duplicate policy, immutable ICP profiles and reasons | CSV/scoring tests and import browser journey |
| Structured AI and human review | Strict qualification/draft schemas, revision/hash-bound approval, labelled mock receipts | Stale-review, current-permission, changed-facts and mock-send tests |
| Integrations | Real public GitHub metadata, signed/deduplicated ingress, outgoing attempt history and safe retry contract | Real read-only GitHub smoke check; webhook security/database/browser tests |
| Dashboard and monitoring | Scoped API-backed analytics/chart, exact data table, status/age/latency signals | Analytics API and desktop/mobile browser assertions |
| Operations | Locked/audited dependencies, digest-pinned containers, private env generation, production ingress profile, backup/restore | CI build/audits, Caddy validation and isolated restored business-count comparison |
| Demonstration | Recorded fictional import → score → review → simulated receipt, retry and viewer denial | Successful Docker-backed browser recording |
| Public deployment | Not performed | Requires approved merge, actual host/domain and post-deploy smoke checks |

AI/email remain explicit mock/disabled adapters under the supplied credential fallback instruction. No live AI request or real email send is claimed. Retention limits and erasure limitations are documented in RETENTION.md. Broader self-service erasure, verification/reset mail and external alerting are not advertised as implemented.
