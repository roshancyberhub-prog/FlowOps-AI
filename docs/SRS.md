# Software requirements and acceptance

The normative functional and non-functional requirements remain in [REQUIREMENTS.md](REQUIREMENTS.md). This document maps the current foundation to verification.

| Requirement | Foundation behavior | Evidence |
|---|---|---|
| Authentication | Register, sign in, expire/revoke session | API and browser tests |
| Organization access | Backend membership checks, role policies | Cross-tenant and viewer tests |
| Lead management | Scoped CRUD, search, pagination, archive/restore | API and browser journeys |
| Validation | Normalization, field/size limits, duplicate conflict | Unit/API regression tests |
| Auditability | Transactional mutation events, restricted history | Implemented API; role denial test |
| Local operation | PostgreSQL, Redis, migration, API, frontend containers | CI Compose startup and readiness |

Workflow editing, execution, CSV imports, AI processing and integrations remain later milestone requirements. Responsive layout is checked against actual screenshots and browser geometry, not inferred from a successful build. Acceptance status is maintained in the implementation checklist.
