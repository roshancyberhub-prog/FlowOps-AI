import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import now
from app.execution.hashing import payload_hash
from app.leads.csv_import import inspect_csv, validate_mapping
from app.models import ImportJob, Membership, Organization, OutboxEntry
from app.services.leads import audit


def enqueue_import(
    session: AsyncSession, job: ImportJob, available_at: datetime | None = None
) -> None:
    job.dispatch_generation += 1
    job.next_run_at = available_at or now()
    session.add(
        OutboxEntry(
            import_job_id=job.id,
            dispatch_key=f"import:{job.id}:{job.dispatch_generation}",
            available_at=job.next_run_at,
        )
    )


async def get_import(session: AsyncSession, member: Membership, job_id: UUID) -> ImportJob:
    job = await session.scalar(
        select(ImportJob).where(
            ImportJob.id == job_id, ImportJob.organization_id == member.organization_id
        )
    )
    if job is None:
        raise HTTPException(404, "Import not found.")
    return job


async def accept_import(
    session: AsyncSession,
    member: Membership,
    filename: str,
    data: bytes,
    mapping: dict[str, str],
    key: str,
    request_id: str,
) -> tuple[ImportJob, bool]:
    inspected = inspect_csv(data)
    validate_mapping(inspected["headers"], mapping)
    file_hash = hashlib.sha256(data).hexdigest()
    digest = payload_hash(
        {"file_hash": file_hash, "mapping": mapping, "filename": filename, "policy": "skip"}
    )
    org_id = member.organization_id
    await session.scalar(select(Organization).where(Organization.id == org_id).with_for_update())
    existing = await session.scalar(
        select(ImportJob).where(
            ImportJob.organization_id == org_id, ImportJob.idempotency_key == key
        )
    )
    if existing:
        if existing.input_hash != digest:
            raise HTTPException(
                409, "This idempotency key was already used for a different import."
            )
        return existing, False
    active = await session.scalar(
        select(func.count())
        .select_from(ImportJob)
        .where(
            ImportJob.organization_id == org_id,
            ImportJob.status.in_(["queued", "running", "retrying"]),
        )
    )
    if active and active >= 10:
        raise HTTPException(429, "Wait for existing imports to finish before uploading another.")
    job = ImportJob(
        organization_id=org_id,
        requested_by=member.user_id,
        filename=filename,
        file_hash=file_hash,
        source_data=data,
        column_mapping=mapping,
        idempotency_key=key,
        input_hash=digest,
        total_rows=inspected["row_count"],
        correlation_id=request_id,
    )
    session.add(job)
    try:
        await session.flush()
        enqueue_import(session, job)
        audit(session, member, "import.requested", job.id, request_id)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "Conflicting import request.") from exc
    return job, True


async def expire_import_sources(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as session:
        jobs = await session.scalars(
            select(ImportJob)
            .where(
                ImportJob.status.in_(["queued", "running", "retrying"]),
                ImportJob.created_at < now() - timedelta(days=7),
            )
            .with_for_update(skip_locked=True)
            .limit(100)
        )
        for job in jobs:
            job.status = "failed"
            job.source_data = None
            job.completed_at = now()
            job.error_code = "IMPORT_EXPIRED"
            job.error_summary = (
                "This upload expired after seven days. Upload the file again to continue."
            )
        await session.commit()
