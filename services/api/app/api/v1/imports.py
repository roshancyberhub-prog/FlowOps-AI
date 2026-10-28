from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.leads.csv_import import MAX_BYTES, ImportValidation, inspect_csv
from app.models import ImportJob, ImportRow, Membership
from app.schemas.imports import ImportRead, ImportRowRead
from app.security.permissions import WRITE_ROLES, membership, require_role
from app.services.imports import accept_import, get_import

router = APIRouter(prefix="/leads/imports", tags=["CSV imports"])


async def read_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not filename.lower().endswith(".csv") or len(filename) > 200:
        raise HTTPException(422, "Choose a .csv file with a filename up to 200 characters.")
    if file.content_type not in {
        "text/csv",
        "text/plain",
        "application/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }:
        raise HTTPException(422, "Upload a text CSV file.")
    data = bytearray()
    try:
        while chunk := await file.read(64 * 1024):
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise HTTPException(413, "CSV files must be 512 KiB or smaller.")
    finally:
        await file.close()
    return filename, bytes(data)


@router.post("/preview")
async def preview(file: UploadFile = File(...), member: Membership = Depends(membership)) -> dict:
    require_role(member, WRITE_ROLES)
    _, data = await read_upload(file)
    try:
        return inspect_csv(data)
    except ImportValidation as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("", response_model=ImportRead, status_code=202)
async def start_import(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    column_mapping: str = Form(..., max_length=5000),
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str = Header(
        alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9:_-]+$"
    ),
) -> ImportJob:
    require_role(member, WRITE_ROLES)
    filename, data = await read_upload(file)
    try:
        mapping = TypeAdapter(dict[str, str]).validate_json(column_mapping)
        job, created = await accept_import(
            session, member, filename, data, mapping, idempotency_key, request.state.request_id
        )
    except (ImportValidation, ValidationError) as exc:
        message = (
            str(exc)
            if isinstance(exc, ImportValidation)
            else "Provide a JSON mapping of lead fields to CSV columns."
        )
        raise HTTPException(422, message) from exc
    response.status_code = 202 if created else 200
    return job


@router.get("")
async def list_imports(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
) -> dict:
    condition = ImportJob.organization_id == member.organization_id
    rows = await session.scalars(
        select(ImportJob)
        .where(condition)
        .order_by(ImportJob.created_at.desc(), ImportJob.id)
        .offset((page - 1) * 25)
        .limit(25)
    )
    total = await session.scalar(select(func.count()).select_from(ImportJob).where(condition))
    return {
        "items": [ImportRead.model_validate(row) for row in rows],
        "total": total or 0,
        "page": page,
        "page_size": 25,
    }


@router.get("/{job_id}", response_model=ImportRead)
async def detail(
    job_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> ImportJob:
    return await get_import(session, member, job_id)


@router.get("/{job_id}/rows")
@router.get("/{job_id}/errors")
async def rows(
    job_id: UUID,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    status: Literal["inserted", "invalid", "duplicate"] | None = None,
) -> dict:
    await get_import(session, member, job_id)
    conditions = [ImportRow.import_job_id == job_id]
    if request.url.path.endswith("/errors"):
        status = "invalid"
    if status:
        conditions.append(ImportRow.status == status)
    result = await session.scalars(
        select(ImportRow)
        .where(*conditions)
        .order_by(ImportRow.row_number)
        .offset((page - 1) * 100)
        .limit(100)
    )
    total = await session.scalar(select(func.count()).select_from(ImportRow).where(*conditions))
    return {
        "items": [ImportRowRead.model_validate(row) for row in result],
        "total": total or 0,
        "page": page,
        "page_size": 100,
    }
