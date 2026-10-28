import asyncio
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import now
from app.execution.errors import FailureInfo, classify_error, retry_delay
from app.execution.triggers import lead_created
from app.leads.csv_import import ParsedRow, parse_csv
from app.models import AuditLog, ImportJob, ImportRow, Lead, Membership, User
from app.services.imports import enqueue_import
from app.services.leads import audit

BATCH_SIZE = 100


async def import_record(session: AsyncSession, job: ImportJob, row: ParsedRow) -> str:
    status = "invalid" if row.errors else "duplicate" if row.duplicate_in_file else "inserted"
    errors = row.errors.copy()
    lead_id = None
    if row.duplicate_in_file:
        errors.append(
            {
                "field": "email",
                "message": "An earlier valid record in this file has the same email.",
            }
        )
    if status == "inserted":
        existing = await session.scalar(
            select(Lead.id)
            .where(Lead.organization_id == job.organization_id, Lead.email == row.data["email"])
            .limit(1)
        )
        if existing:
            status = "duplicate"
            errors.append(
                {
                    "field": "email",
                    "message": "This email exists in the workspace, including archived records.",
                }
            )
        else:
            try:
                async with session.begin_nested():
                    lead = Lead(organization_id=job.organization_id, **row.data)
                    session.add(lead)
                    await session.flush()
                    await lead_created(session, lead, job.correlation_id)
                    lead_id = lead.id
                    session.add(
                        AuditLog(
                            organization_id=job.organization_id,
                            actor_user_id=job.requested_by,
                            action="lead.imported",
                            resource_id=str(lead.id),
                            correlation_id=job.correlation_id,
                        )
                    )
            except IntegrityError as exc:
                if "uq_lead_organization_email" not in str(exc.orig):
                    raise
                status = "duplicate"
                errors.append(
                    {"field": "email", "message": "Another request already inserted this email."}
                )
    session.add(
        ImportRow(
            import_job_id=job.id,
            row_number=row.number,
            status=status,
            email=row.data.get("email"),
            input_values=row.raw,
            errors=errors,
            lead_id=lead_id,
        )
    )
    return status


async def process_batch(factory: async_sessionmaker[AsyncSession], job_id: UUID) -> None:
    async with factory() as session:
        job = await session.scalar(
            select(ImportJob).where(ImportJob.id == job_id).with_for_update()
        )
        if job is None or job.status in {"succeeded", "failed"} or job.next_run_at > now():
            return
        member = await session.scalar(
            select(Membership).where(
                Membership.organization_id == job.organization_id,
                Membership.user_id == job.requested_by,
            )
        )
        user = await session.get(User, job.requested_by)
        if (
            member is None
            or member.role not in {"owner", "admin", "member"}
            or user is None
            or not user.is_active
        ):
            job.status = "failed"
            job.error_code = "PERMISSION_REVOKED"
            job.error_summary = "The importing user no longer has permission to create leads."
            job.completed_at = now()
            job.source_data = None
            await session.commit()
            return
        if job.source_data is None:
            raise ValueError("Import source unavailable")
        rows = parse_csv(job.source_data, job.column_mapping)
        job.status = "running"
        job.started_at = job.started_at or now()
        for row in rows[job.processed_rows : job.processed_rows + BATCH_SIZE]:
            status = await import_record(session, job, row)
            job.processed_rows += 1
            if status == "inserted":
                job.inserted_rows += 1
            elif status == "invalid":
                job.invalid_rows += 1
            else:
                job.duplicate_rows += 1
        job.error_code = job.error_summary = None
        if job.processed_rows == job.total_rows:
            job.status = "succeeded"
            job.completed_at = now()
            job.source_data = None
            audit(session, member, "import.completed", job.id, job.correlation_id)
        else:
            enqueue_import(session, job)
        await session.commit()


async def process_import(factory: async_sessionmaker[AsyncSession], job_id: UUID) -> None:
    try:
        async with asyncio.timeout(90):
            await process_batch(factory, job_id)
    except Exception as exc:
        failure = classify_error(exc, "database")
        if failure.code == "NODE_ERROR":
            failure = FailureInfo(
                "IMPORT_PROCESSING_ERROR",
                "The import could not complete. Review the file and processing report.",
                False,
            )
        elif failure.code == "NODE_TIMEOUT":
            failure = FailureInfo(
                "IMPORT_BATCH_TIMEOUT",
                "The batch exceeded its time limit; its changes were rolled back.",
                True,
            )
        if isinstance(exc, DBAPIError) and (
            exc.connection_invalidated
            or getattr(exc.orig, "sqlstate", None) in {"40001", "40P01", "08006", "53300"}
        ):
            failure = FailureInfo(
                "IMPORT_DATABASE_UNAVAILABLE",
                "The database was temporarily unavailable; the batch was rolled back.",
                True,
            )
        async with factory() as session:
            job = await session.scalar(
                select(ImportJob).where(ImportJob.id == job_id).with_for_update()
            )
            if job is None or job.status in {"succeeded", "failed"}:
                return
            job.failure_count += 1
            job.error_code = failure.code
            job.error_summary = failure.summary
            if failure.retryable and job.failure_count < 3:
                job.status = "retrying"
                enqueue_import(
                    session, job, now() + timedelta(seconds=retry_delay(job.failure_count))
                )
            else:
                job.status = "failed"
                job.completed_at = now()
                job.source_data = None
            await session.commit()
