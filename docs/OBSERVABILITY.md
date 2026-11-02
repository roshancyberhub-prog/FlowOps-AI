# Monitoring

The operating questions are: are requests failing or slowing down; is background work overdue; and which integration deliveries need reconciliation?

| Question | Implemented signal | First response |
|---|---|---|
| API failures/latency | JSON `request_completed`: normalized route (including unknown paths), method, status, duration_ms, request_id | Compare 5xx counts and p95 with the last healthy release; inspect a request ID |
| API dependencies available | `/api/v1/health/ready` checks PostgreSQL + Redis | Restore the unavailable dependency; do not bypass fail-closed rate limits |
| Worker/scheduler functioning | Authenticated `/execution-health`: dispatch heartbeat, oldest due age, status counts, pending imports and webhook outcomes | Inspect worker/scheduler logs; keep one Beat process; preserve outbox rows |
| A particular workflow failed | Persistent execution/step history and `step_completed` JSON with request/execution/node IDs, attempt, duration and safe error code | Inspect the immutable version and failed attempt; retry only if eligible |
| External result uncertain | Webhook attempt history with HTTP status/error code/uncertainty | Reconcile with the receiver before any replacement event |
| Business outcomes | Overview API and Recharts seven-day chart, exact daily table, workflow run counts/last run | Compare succeeded/failed counts; success rate excludes cancelled/incomplete runs |

Export a bounded metrics report from application JSON logs:

```bash
bash scripts/compose.sh logs --since 10m --no-log-prefix --no-color api | python3 scripts/log-summary.py
```

The script summarizes the last 100000 request events by normalized route/method, returns request/5xx counts, p50/p95/p99 durations and cumulative duration buckets, and discards other fields. A 10-minute export gives request rate by dividing counts by 600 seconds. Do not label a monitoring time series with request IDs, account IDs, raw URLs or email addresses. Request IDs belong in restricted logs. `step_completed` events also expose trigger type and run mode for attribution.

On the actual host, forward JSON logs to the chosen monitoring sink, collect container CPU/memory/disk and database connection utilization, and configure actionable alerts. Initial portfolio targets: 99% successful API responses (excluding expected 4xx), p95 below 1 second for normal data reads, and no eligible work overdue by more than 5 minutes. Establish a baseline before treating these as achieved SLOs. Page for readiness failure over 1 minute, API 5xx above 1% for 5 minutes, or due-work age over 5 minutes; investigate terminal/uncertain deliveries promptly. Link alerts to [RUNBOOK.md](RUNBOOK.md). Test the actual alert destination before launch.

The log fields, metrics summarizer and scoped health signals are implemented and tested. CI demonstrates a real mock-provider transient failure followed by a successful retry with the same correlated execution. No external error-monitoring account, distributed tracing backend, live alert destination or public-host performance measurement has been configured or claimed.
