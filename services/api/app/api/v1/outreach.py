from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.models import (
    EmailDelivery,
    EmailDraft,
    Membership,
    Workflow,
    WorkflowExecution,
    WorkflowVersion,
)
from app.schemas.executions import ExecutionRead, RunRequest
from app.schemas.outreach import DeliveryRead, DraftEdit, DraftRead, DraftRunRequest
from app.security.permissions import WRITE_ROLES, membership, require_role
from app.services.drafts import edit_draft, get_draft
from app.services.executions import request_execution
from app.services.leads import get_lead
from app.workflows.graph import validate_graph

router = APIRouter(tags=["outreach drafts"])


@router.get("/providers/status")
async def provider_status(member: Membership = Depends(membership)) -> dict:
    settings = get_settings()
    return {
        "ai_provider": settings.ai_provider,
        "email_provider": settings.email_provider,
        "live_ai_available": False,
        "live_email_available": False,
    }


def draft_read(draft: EmailDraft, status: str) -> DraftRead:
    return DraftRead.model_validate(draft).model_copy(update={"execution_status": status})


@router.get("/leads/{lead_id}/drafts")
async def list_drafts(
    lead_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1, le=10000),
) -> dict:
    await get_lead(session, member.organization_id, lead_id)
    conditions = [
        EmailDraft.organization_id == member.organization_id,
        EmailDraft.lead_id == lead_id,
    ]
    rows = await session.execute(
        select(EmailDraft, WorkflowExecution.status)
        .join(WorkflowExecution, WorkflowExecution.id == EmailDraft.execution_id)
        .where(*conditions)
        .order_by(EmailDraft.created_at.desc(), EmailDraft.id)
        .offset((page - 1) * 25)
        .limit(25)
    )
    total = await session.scalar(select(func.count()).select_from(EmailDraft).where(*conditions))
    return {
        "items": [draft_read(draft, status) for draft, status in rows],
        "total": total or 0,
        "page": page,
        "page_size": 25,
    }


@router.post("/leads/{lead_id}/drafts", response_model=ExecutionRead, status_code=202)
async def queue_draft(
    lead_id: UUID,
    data: DraftRunRequest,
    request: Request,
    response: Response,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str = Header(
        alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9:_-]+$"
    ),
) -> WorkflowExecution:
    require_role(member, WRITE_ROLES)
    run, created = await request_execution(
        session,
        member,
        data.workflow_id,
        RunRequest(lead_id=lead_id, workflow_version_id=data.workflow_version_id),
        idempotency_key,
        request.state.request_id,
        data.mode,
        required_node_type="action.generate_email_draft",
    )
    response.status_code = 202 if created else 200
    return run


@router.get("/drafts/{draft_id}", response_model=DraftRead)
async def detail(
    draft_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> DraftRead:
    draft = await get_draft(session, member, draft_id)
    run = await session.get(WorkflowExecution, draft.execution_id)
    assert run is not None
    return draft_read(draft, run.status)


@router.patch("/drafts/{draft_id}", response_model=DraftRead)
async def edit(
    draft_id: UUID,
    data: DraftEdit,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> DraftRead:
    require_role(member, WRITE_ROLES)
    draft = await edit_draft(session, member, draft_id, data, request.state.request_id)
    run = await session.get(WorkflowExecution, draft.execution_id)
    assert run is not None
    return draft_read(draft, run.status)


@router.get("/deliveries")
async def deliveries(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    execution_id: UUID | None = None,
    draft_id: UUID | None = None,
    page: int = Query(1, ge=1, le=10000),
) -> dict:
    conditions = [EmailDelivery.organization_id == member.organization_id]
    if execution_id:
        conditions.append(EmailDelivery.execution_id == execution_id)
    if draft_id:
        conditions.append(EmailDelivery.draft_id == draft_id)
    rows = await session.scalars(
        select(EmailDelivery)
        .where(*conditions)
        .order_by(EmailDelivery.created_at.desc(), EmailDelivery.id)
        .offset((page - 1) * 25)
        .limit(25)
    )
    total = await session.scalar(select(func.count()).select_from(EmailDelivery).where(*conditions))
    return {
        "items": [DeliveryRead.model_validate(row) for row in rows],
        "total": total or 0,
        "page": page,
        "page_size": 25,
    }


@router.get("/leads/{lead_id}/draft-workflows")
async def draft_workflows(
    lead_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1, le=10000),
) -> dict:
    await get_lead(session, member.organization_id, lead_id)
    conditions = [
        Workflow.organization_id == member.organization_id,
        Workflow.status == "active",
        WorkflowVersion.graph_definition["nodes"].contains(
            [{"type": "action.generate_email_draft"}]
        ),
    ]
    rows = await session.execute(
        select(Workflow, WorkflowVersion)
        .join(WorkflowVersion, Workflow.current_version_id == WorkflowVersion.id)
        .where(*conditions)
        .order_by(Workflow.updated_at.desc(), Workflow.id)
        .offset((page - 1) * 25)
        .limit(25)
    )
    total = await session.scalar(
        select(func.count())
        .select_from(Workflow)
        .join(WorkflowVersion, Workflow.current_version_id == WorkflowVersion.id)
        .where(*conditions)
    )
    return {
        "items": [
            {
                "workflow_id": workflow.id,
                "name": workflow.name,
                "version_id": version.id,
                "version_number": version.version_number,
                "can_run": validate_graph(version.graph_definition, member.role).valid,
            }
            for workflow, version in rows
        ],
        "total": total or 0,
        "page": page,
        "page_size": 25,
    }
