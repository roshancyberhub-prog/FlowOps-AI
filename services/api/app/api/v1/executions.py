from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import ExecutionStep, Membership, WorkflowExecution
from app.schemas.executions import (
    ExecutionPage,
    ExecutionRead,
    ExecutionStatus,
    RunRequest,
    StepRead,
)
from app.security.permissions import ADMIN_ROLES, WRITE_ROLES, membership, require_role
from app.services.executions import get_execution, request_execution

router = APIRouter(tags=["executions"])


@router.post("/workflows/{workflow_id}/test-runs", response_model=ExecutionRead, status_code=202)
@router.post("/workflows/{workflow_id}/runs", response_model=ExecutionRead, status_code=202)
async def run_workflow(
    workflow_id: UUID,
    data: RunRequest,
    request: Request,
    response: Response,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str = Header(
        alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9:_-]+$"
    ),
) -> WorkflowExecution:
    require_role(member, WRITE_ROLES)
    execution, created = await request_execution(
        session,
        member,
        workflow_id,
        data,
        idempotency_key,
        request.state.request_id,
        "test" if request.url.path.endswith("/test-runs") else "live",
    )
    response.status_code = 202 if created else 200
    return execution


@router.get("/executions", response_model=ExecutionPage)
async def list_executions(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status: ExecutionStatus | None = None,
    workflow_id: UUID | None = None,
) -> ExecutionPage:
    conditions = [WorkflowExecution.organization_id == member.organization_id]
    if status:
        conditions.append(WorkflowExecution.status == status)
    if workflow_id:
        conditions.append(WorkflowExecution.workflow_id == workflow_id)
    total = await session.scalar(
        select(func.count()).select_from(WorkflowExecution).where(*conditions)
    )
    rows = await session.scalars(
        select(WorkflowExecution)
        .where(*conditions)
        .order_by(WorkflowExecution.created_at.desc(), WorkflowExecution.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ExecutionPage(
        items=[ExecutionRead.model_validate(row) for row in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/executions/{execution_id}", response_model=ExecutionRead)
async def execution(
    execution_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> WorkflowExecution:
    return await get_execution(session, member, execution_id)


@router.get("/executions/{execution_id}/steps")
async def steps(
    execution_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
) -> dict:
    await get_execution(session, member, execution_id)
    rows = await session.scalars(
        select(ExecutionStep)
        .where(ExecutionStep.execution_id == execution_id)
        .order_by(ExecutionStep.started_at, ExecutionStep.id)
        .offset((page - 1) * 100)
        .limit(100)
    )
    items = []
    for row in rows:
        value = StepRead.model_validate(row)
        if member.role not in ADMIN_ROLES:
            value.error_frames = []
        items.append(value)
    total = await session.scalar(
        select(func.count())
        .select_from(ExecutionStep)
        .where(ExecutionStep.execution_id == execution_id)
    )
    return {"items": items, "total": total or 0, "page": page, "page_size": 100}
