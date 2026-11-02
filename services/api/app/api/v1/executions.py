from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import now
from app.db.session import get_session
from app.models import (
    ApprovalRequest,
    ExecutionStep,
    ImportJob,
    Membership,
    WebhookDelivery,
    WorkerHeartbeat,
    WorkflowExecution,
)
from app.schemas.executions import (
    ApprovalDecision,
    ApprovalRead,
    ExecutionPage,
    ExecutionRead,
    ExecutionStatus,
    RunRequest,
    StepRead,
)
from app.security.permissions import ADMIN_ROLES, WRITE_ROLES, membership, require_role
from app.services.execution_controls import cancel_execution, decide_approval, retry_execution
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
    page: int = Query(default=1, ge=1, le=10000),
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
    page: int = Query(default=1, ge=1, le=10000),
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


@router.post("/executions/{execution_id}/cancel", response_model=ExecutionRead)
async def cancel(
    execution_id: UUID,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> WorkflowExecution:
    require_role(member, WRITE_ROLES)
    return await cancel_execution(session, member, execution_id, request.state.request_id)


@router.post("/executions/{execution_id}/retry", response_model=ExecutionRead)
async def retry(
    execution_id: UUID,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> WorkflowExecution:
    require_role(member, WRITE_ROLES)
    return await retry_execution(session, member, execution_id, request.state.request_id)


@router.get("/approvals")
async def approvals(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1, le=10000),
    status: Literal["pending", "approved", "rejected", "expired", "cancelled"] | None = None,
) -> dict:
    conditions = [ApprovalRequest.organization_id == member.organization_id]
    if status:
        conditions.append(ApprovalRequest.status == status)
    rows = await session.scalars(
        select(ApprovalRequest)
        .where(*conditions)
        .order_by(ApprovalRequest.requested_at.desc(), ApprovalRequest.id)
        .offset((page - 1) * 25)
        .limit(25)
    )
    total = await session.scalar(
        select(func.count()).select_from(ApprovalRequest).where(*conditions)
    )
    return {
        "items": [ApprovalRead.model_validate(row) for row in rows],
        "total": total or 0,
        "page": page,
        "page_size": 25,
    }


@router.post("/approvals/{approval_id}/{decision}", response_model=ApprovalRead)
async def decide(
    approval_id: UUID,
    decision: Literal["approve", "reject"],
    data: ApprovalDecision,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> ApprovalRequest:
    require_role(member, ADMIN_ROLES)
    return await decide_approval(
        session,
        member,
        approval_id,
        "approved" if decision == "approve" else "rejected",
        data,
        request.state.request_id,
    )


@router.get("/approvals/{approval_id}", response_model=ApprovalRead)
async def approval_detail(
    approval_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> ApprovalRequest:
    result = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == member.organization_id,
        )
    )
    if result is None:
        raise HTTPException(404, "Approval not found.")
    return result


@router.get("/execution-health")
async def execution_health(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> dict:
    last_seen = await session.scalar(
        select(WorkerHeartbeat.last_seen).where(WorkerHeartbeat.worker_name == "dispatcher")
    )
    counts = await session.execute(
        select(WorkflowExecution.status, func.count())
        .where(WorkflowExecution.organization_id == member.organization_id)
        .group_by(WorkflowExecution.status)
    )
    statuses = {status: count for status, count in counts}
    oldest = await session.scalar(
        select(func.min(WorkflowExecution.next_run_at)).where(
            WorkflowExecution.organization_id == member.organization_id,
            WorkflowExecution.status.in_(["queued", "running", "retrying"]),
            WorkflowExecution.next_run_at < now(),
        )
    )
    imports = await session.scalar(
        select(func.count())
        .select_from(ImportJob)
        .where(
            ImportJob.organization_id == member.organization_id,
            ImportJob.status.in_(["queued", "running", "retrying"]),
        )
    )
    deliveries = await session.execute(
        select(WebhookDelivery.status, func.count())
        .where(WebhookDelivery.organization_id == member.organization_id)
        .group_by(WebhookDelivery.status)
    )
    return {
        "status": "operational"
        if last_seen and (now() - last_seen).total_seconds() < 30
        else "unavailable",
        "last_dispatch_at": last_seen,
        "oldest_due_seconds": round((now() - oldest).total_seconds()) if oldest else 0,
        "executions_by_status": statuses,
        "pending_imports": imports or 0,
        "webhooks_by_status": {status: count for status, count in deliveries},
    }
