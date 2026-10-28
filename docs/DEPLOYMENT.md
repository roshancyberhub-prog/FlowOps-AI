# Deployment status

No application has been deployed to a public host. CI runs a disposable Docker deployment for verification; this is not a live demo or a production environment.

The current foundation can run on a Docker host with PostgreSQL and Redis. Production configuration requires HTTPS, APP_ENV=production, the exact WEB_ORIGIN, private database/Redis networking, and a trusted ingress. The frontend API destination is chosen during its Docker build through API_INTERNAL_URL. Keep the API and web behind one browser origin, or design an explicit cross-origin authentication policy before separating them.

Use a migration release step before starting new API instances. CI verifies migration reversibility on a disposable database; never downgrade a populated production database without a reviewed data and recovery plan. Container images currently use versioned base tags; image digest pinning, external secret provisioning, backup verification and monitoring are release work still to complete.

When workflows arrive, the selected host must support persistent Celery workers and a scheduler. A Next.js/serverless frontend host cannot replace that worker infrastructure. Do not advertise production readiness until every milestone in CHATGPT.md has passed.
