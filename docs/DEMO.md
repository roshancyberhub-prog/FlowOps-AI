# Recorded demonstration

[Watch the verified FlowOps AI demo](demo/flowops-ai-demo.mp4).

This recording is from the actual successful Chromium journey in CI run [41030254236](https://github.com/roshancyberhub-prog/FlowOps-AI/actions/runs/41030254236), against PostgreSQL, Redis, FastAPI, Next.js, a separate Celery worker and Beat. It uses fictional accounts/leads and explicitly labelled mock AI/email. It is compressed from the original 1440×1100 browser recording; no application screens were fabricated. No real external email was sent.

The journey signs up, creates a workspace, publishes the outreach graph, imports fitting/invalid/duplicate rows, inspects reports, scores and drafts through background workers, edits a draft, rejects a stale review, approves one exact revision, rejects the other, and inspects nine successful steps plus a simulated receipt. It then verifies signed webhook deduplication/rejection, views real database analytics on desktop/mobile, shows a mock-provider transient failure followed by a successful retry, and switches to an independently authenticated viewer to show that approval controls are unavailable. Automated requests in the same journey also assert viewer approval denial (403) and execution access denial under another workspace (404).

## Reproduce

Start the documented local Docker setup. For the recorded retry scenario only, set `DEMO_RETRY_FAILURE=true` in `.env` and recreate API, worker and scheduler:

```bash
docker compose up -d --force-recreate api worker scheduler
cd apps/web
npx playwright install chromium
E2E_EXTERNAL=1 npx playwright test tests/imports.spec.ts
```

Use a fresh fictional test database for the entire browser suite so shared development-IP rate buckets are not already exhausted. Do not disable rate limiting to work around repeated manual test runs; wait for the documented windows. The setup must have a generated signing key. Playwright writes the video and screenshots under `apps/web/test-results/`; CI uploads them as browser-verification. Set `DEMO_RETRY_FAILURE=false` again when finished. The production profile forces it off, and the code ignores the fault in production or live execution mode.
