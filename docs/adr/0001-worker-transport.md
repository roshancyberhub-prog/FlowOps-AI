# Worker transport compatibility

Celery 5.6.3 and stable Kombu 5.6.2 are used with Redis client 6.4.0. Kombu's stable Redis transport requires redis-py below 6.5; retaining redis-py 8 would force a prerelease Kombu transport. The lockfile therefore pins a supported stable combination. Redis server 7 remains unchanged.

Workflow state and results will live in PostgreSQL. Redis is the broker, not the source of truth. Dispatch intent must commit with each accepted execution, and repeat delivery must be safe. Celery task acknowledgements do not by themselves guarantee application idempotency.

References: [Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html), [Redis transport](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html).
