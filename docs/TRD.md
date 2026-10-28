# Technical decisions

- Modular monolith: one FastAPI codebase, explicit API/schema/service/security boundaries. PostgreSQL is the source of truth.
- Next.js App Router with React/TypeScript, Tailwind, shadcn-style Button, TanStack Query and React Hook Form/Zod. Data comes from the backend, not client-side demo metrics.
- FastAPI Users SQLAlchemy database sessions were selected to provide maintained password handling and token generation/revocation without depending on an external identity account. See the provider's [database strategy documentation](https://fastapi-users.github.io/fastapi-users/latest/configuration/authentication/strategies/database/).
- Same-origin Next.js API proxy keeps browser cookies HttpOnly and avoids unnecessary cross-origin credential configuration. Production uses Secure cookies and HTTPS.
- Async SQLAlchemy/asyncpg and Alembic provide durable storage and migrations. Database uniqueness enforces the organization/email duplicate policy under concurrent requests.
- A Redis Lua increment/expiry script enforces rate windows atomically across API instances. Redis failure produces 503; limits do not silently disappear.
- Docker Compose separates migration, API and web startup and verifies readiness. CI tests the documented containers against real PostgreSQL/Redis.

Python and frontend lockfiles pin dependencies. JavaScript install scripts are disabled; native prebuilt optional packages supply the Next.js/Tailwind build dependencies. There is no Celery execution code yet, and no external AI/email/CRM credential is configured.
