# CSV imports

The CSV backend accepts UTF-8 `.csv` files up to **512 KiB**, **2,000 nonempty records**, **30 columns** and **2,048 characters per cell**. Headers are unique ignoring case, nonempty and at most 100 characters. Quoted commas/newlines and a UTF-8 BOM are supported. Blank records are ignored. A record number counts CSV records, with the header as record 1.

The UI previews headers and suggests mappings. Name and email are required; each source column can map to one supported lead input. Scores, tenant identifiers and statuses cannot be imported. Unmapped columns are ignored and do not appear in row reports. Structural/file/mapping errors reject the request; field-level errors become invalid-record results.

The duplicate policy is insert valid new leads and **skip** duplicates. Normalized email is unique within the organization, including archived leads. The first valid file record wins; later occurrences are skipped. Existing leads are preserved. Concurrent inserts are protected by the database constraint.

An accepted request saves the bounded raw source, import record and outbox intent in PostgreSQL. Celery processes batches of 100 records. Leads, audit events, automatic lead-created workflow intents, row results, progress and next dispatch commit together. A batch rollback preserves earlier committed batches and discards its own changes. Row/job locks and unique record identifiers tolerate duplicate worker messages. Lost dispatches are reconciled from PostgreSQL. Eligible temporary failures receive up to three failed attempts with backoff; permanent failures stop processing.

Raw source bytes are removed on success or terminal failure. Maintenance expires abandoned uploads after seven days, removes their source and preserves any committed leads/reports. API upload files are closed after bounded reading; there are no retained local upload paths. Row reports retain mapped input values and errors as organization-owned history; production report-retention/deletion policy remains release work.

Routes under `/api/v1`, authenticated and scoped by `X-Organization-ID`:

| Method | Route | Behavior |
|---|---|---|
| POST | `/leads/imports/preview` | Bounded multipart `file`; return headers, record count and suggested mapping |
| POST | `/leads/imports` | Multipart `file` and JSON string `column_mapping`; require Idempotency-Key |
| GET | `/leads/imports` | History, 25 per page |
| GET | `/leads/imports/{id}` | Progress, counters and failure summary |
| GET | `/leads/imports/{id}/rows` | Results, 100 per page; optional inserted/invalid/duplicate status |
| GET | `/leads/imports/{id}/errors` | Invalid records, 100 per page |

Owners/admins/members can upload; viewers can read reports. The idempotency digest binds file bytes, filename, mapping and duplicate policy. Identical replay returns the original job; conflicting reuse returns 409. At most ten imports per organization can be active. A failed import can be resubmitted with a new idempotency key; prior inserted leads will be recognized as duplicates.

The fictional sample in `apps/web/public/sample-leads.csv` contains valid, invalid and duplicate records. No external messages are sent by importing a file alone. Matching published lead-created workflows may run; their permissions and protected-send approval rules still apply.
