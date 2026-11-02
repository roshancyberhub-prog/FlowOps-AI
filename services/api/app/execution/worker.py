import asyncio
import logging
from datetime import timedelta
from uuid import UUID

from celery import Celery
from celery.signals import setup_logging
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import configure_logging, json_handler
from app.db.base import now
from app.execution.engine import finish, process_execution
from app.execution.triggers import schedule_due
from app.models import (
    AccessToken,
    ApprovalRequest,
    ExecutionStep,
    ImportJob,
    OutboxEntry,
    WorkerHeartbeat,
    WorkflowExecution,
)
from app.services.imports import expire_import_sources

configure_logging()
settings = get_settings()
celery_app = Celery("flowops", broker=str(settings.redis_url))
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=3,
    broker_transport_options={
        "visibility_timeout": 300,
        "socket_connect_timeout": 3,
        "socket_timeout": 3,
    },
    task_soft_time_limit=120,
    task_time_limit=150,
    beat_schedule={
        "dispatch-outbox": {"task": "flowops.dispatch", "schedule": 3.0},
        "dispatch-webhooks": {"task": "flowops.webhooks", "schedule": 5.0},
        "clean-expired-sessions": {"task": "flowops.maintenance", "schedule": 300.0},
    },
)


def worker_sessions() -> async_sessionmaker:
    # Celery invokes asyncio.run per task: never pool asyncpg across event loops.
    return async_sessionmaker(
        create_async_engine(str(settings.database_url), poolclass=NullPool), expire_on_commit=False
    )


async def expire_approvals(factory: async_sessionmaker) -> None:
    async with factory() as session:
        expired = list(
            await session.scalars(
                select(ApprovalRequest)
                .where(ApprovalRequest.status == "pending", ApprovalRequest.expires_at <= now())
                .limit(100)
            )
        )
        for item in expired:
            run = await session.scalar(
                select(WorkflowExecution)
                .where(WorkflowExecution.id == item.execution_id)
                .with_for_update()
            )
            approval = await session.scalar(
                select(ApprovalRequest)
                .where(ApprovalRequest.id == item.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                run
                and approval
                and approval.status == "pending"
                and run.status == "waiting_for_approval"
            ):
                approval.status = "expired"
                approval.decided_at = now()
                step = await session.get(ExecutionStep, approval.execution_step_id)
                if step:
                    step.status = "expired"
                    step.completed_at = now()
                finish(run, "cancelled")
            await session.commit()


async def dispatch_pending() -> None:
    factory = worker_sessions()
    await expire_import_sources(factory)
    await schedule_due(factory)
    await expire_approvals(factory)
    async with factory() as session:
        await session.execute(
            insert(WorkerHeartbeat)
            .values(worker_name="dispatcher", last_seen=now())
            .on_conflict_do_update(index_elements=["worker_name"], set_={"last_seen": now()})
        )
        # A published message can be lost by the broker. Republish overdue runs;
        # row locks and execution leases make duplicate deliveries harmless.
        stale = await session.scalars(
            select(WorkflowExecution)
            .where(
                WorkflowExecution.status.in_(["queued", "retrying", "running"]),
                WorkflowExecution.next_run_at < now() - timedelta(seconds=60),
                (WorkflowExecution.lease_until.is_(None)) | (WorkflowExecution.lease_until < now()),
            )
            .with_for_update(skip_locked=True)
            .limit(100)
        )
        for run in stale:
            latest = await session.scalar(
                select(OutboxEntry)
                .where(OutboxEntry.execution_id == run.id)
                .order_by(OutboxEntry.created_at.desc())
                .limit(1)
            )
            if latest and latest.published_at is not None:
                latest.published_at = None
                latest.available_at = now()
                run.next_run_at = now()
        stale_imports = await session.scalars(
            select(ImportJob)
            .where(
                ImportJob.status.in_(["queued", "running", "retrying"]),
                ImportJob.next_run_at < now() - timedelta(seconds=60),
            )
            .with_for_update(skip_locked=True)
            .limit(100)
        )
        for job in stale_imports:
            latest = await session.scalar(
                select(OutboxEntry)
                .where(OutboxEntry.import_job_id == job.id)
                .order_by(OutboxEntry.created_at.desc())
                .limit(1)
            )
            if latest and latest.published_at is not None:
                latest.published_at = None
                latest.available_at = now()
                job.next_run_at = now()
        await session.commit()
        rows = await session.scalars(
            select(OutboxEntry)
            .where(OutboxEntry.published_at.is_(None), OutboxEntry.available_at <= now())
            .order_by(OutboxEntry.available_at)
            .with_for_update(skip_locked=True)
            .limit(25)
        )
        for entry in rows:
            entry.attempt_count += 1
            try:
                await asyncio.to_thread(
                    celery_app.send_task,
                    "flowops.execute" if entry.execution_id else "flowops.import",
                    args=[str(entry.execution_id or entry.import_job_id)],
                    retry=False,
                )
                entry.published_at = now()
                entry.last_error = None
            except Exception:
                entry.last_error = "BROKER_UNAVAILABLE"
                entry.available_at = now() + timedelta(seconds=10)
        await session.commit()


@celery_app.task(name="flowops.dispatch")
def dispatch() -> None:
    try:
        asyncio.run(dispatch_pending())
    except Exception:
        logging.getLogger("flowops.worker").error("dispatch_failed")


@celery_app.task(name="flowops.execute")
def execute(execution_id: str) -> None:
    try:
        asyncio.run(process_execution(worker_sessions(), UUID(execution_id)))
    except Exception:
        # Durable reconciliation recovers this lease; avoid logging SQL or provider inputs.
        logging.getLogger("flowops.worker").error(
            "execution_task_failed", extra={"execution_id": execution_id}
        )


@setup_logging.connect
def configure_worker_logging(**kwargs: object) -> None:
    configure_logging()
    root = logging.getLogger()
    root.handlers = [json_handler()]
    root.setLevel(logging.WARNING)


@celery_app.task(name="flowops.import")
def import_csv(job_id: str) -> None:
    from app.leads.import_worker import process_import

    try:
        asyncio.run(process_import(worker_sessions(), UUID(job_id)))
    except Exception:
        logging.getLogger("flowops.worker").error("import_task_failed", extra={"import_id": job_id})


@celery_app.task(name="flowops.webhooks")
def webhooks() -> None:
    from app.integrations.worker import dispatch_webhooks

    try:
        asyncio.run(dispatch_webhooks(worker_sessions()))
    except Exception:
        logging.getLogger("flowops.worker").error("webhook_dispatch_failed")


async def cleanup_expired_sessions(factory: async_sessionmaker) -> None:
    async with factory() as session:
        tokens = (
            select(AccessToken.__table__.c.token)
            .where(
                AccessToken.__table__.c.created_at
                < now() - timedelta(seconds=settings.session_lifetime_seconds)
            )
            .limit(1000)
        )
        await session.execute(delete(AccessToken).where(AccessToken.__table__.c.token.in_(tokens)))
        await session.commit()


@celery_app.task(name="flowops.maintenance")
def maintenance() -> None:
    try:
        asyncio.run(cleanup_expired_sessions(worker_sessions()))
    except Exception:
        logging.getLogger("flowops.worker").error("session_cleanup_failed")
