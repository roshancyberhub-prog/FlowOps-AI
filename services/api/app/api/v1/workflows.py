from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Membership, Workflow, WorkflowVersion
from app.schemas.workflows import (
    Revision,
    VersionRead,
    WorkflowCreate,
    WorkflowPage,
    WorkflowPatch,
    WorkflowRead,
)
from app.security.permissions import WRITE_ROLES, membership, require_role
from app.services import workflows
from app.workflows.graph import validate_graph
from app.workflows.registry import REGISTRY
from app.workflows.schema import Graph, ValidationResult
from app.workflows.templates import templates

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/node-types")
async def node_types(member: Membership = Depends(membership)) -> list[dict]:
    return [
        {
            "type": spec.type,
            "title": spec.title,
            "category": spec.category,
            "config_schema": spec.config.model_json_schema(),
            "outputs": spec.outputs,
            "timeout_seconds": spec.timeout_seconds,
            "retryable": spec.retryable,
            "side_effect": spec.side_effect,
            "can_publish": member.role in spec.roles,
        }
        for spec in REGISTRY.values()
    ]


@router.get("/templates")
async def workflow_templates(member: Membership = Depends(membership)) -> list[dict]:
    return templates()


@router.get("", response_model=WorkflowPage)
async def list_workflows(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    status: Literal["draft", "active", "paused", "archived"] | None = None,
) -> WorkflowPage:
    conditions = [Workflow.organization_id == member.organization_id]
    if status:
        conditions.append(Workflow.status == status)
    else:
        conditions.append(Workflow.status != "archived")
    total = await session.scalar(select(func.count()).select_from(Workflow).where(*conditions))
    rows = await session.scalars(
        select(Workflow)
        .where(*conditions)
        .order_by(Workflow.updated_at.desc(), Workflow.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return WorkflowPage(
        items=[WorkflowRead.model_validate(row) for row in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=WorkflowRead, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Workflow:
    require_role(member, WRITE_ROLES)
    return await workflows.create_workflow(session, member, data, request.state.request_id)


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Workflow:
    return await workflows.get_workflow(session, member, workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowPatch,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Workflow:
    require_role(member, WRITE_ROLES)
    return await workflows.update_workflow(
        session, member, workflow_id, data, request.state.request_id
    )


@router.post("/{workflow_id}/validate", response_model=ValidationResult)
async def validate(
    workflow_id: UUID,
    graph: Graph | None = None,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> ValidationResult:
    workflow = await workflows.get_workflow(session, member, workflow_id)
    return validate_graph(graph or workflow.draft_graph, member.role)


@router.post("/{workflow_id}/publish", response_model=WorkflowRead)
async def publish(
    workflow_id: UUID,
    data: Revision,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Workflow:
    require_role(member, WRITE_ROLES)
    return await workflows.publish_workflow(
        session, member, workflow_id, data.expected_revision, request.state.request_id
    )


@router.post("/{workflow_id}/duplicate", response_model=WorkflowRead, status_code=201)
async def duplicate(
    workflow_id: UUID,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Workflow:
    require_role(member, WRITE_ROLES)
    original = await workflows.get_workflow(session, member, workflow_id)
    return await workflows.create_workflow(
        session,
        member,
        WorkflowCreate(
            name=original.name[:143] + " (copy)",
            description=original.description,
            graph=Graph.model_validate(original.draft_graph),
        ),
        request.state.request_id,
    )


@router.post("/{workflow_id}/{action}", response_model=WorkflowRead)
async def change_status(
    workflow_id: UUID,
    action: Literal["pause", "resume", "archive"],
    data: Revision,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Workflow:
    require_role(member, WRITE_ROLES)
    return await workflows.transition(
        session,
        member,
        workflow_id,
        {"pause": "paused", "resume": "active", "archive": "archived"}[action],
        data.expected_revision,
        request.state.request_id,
    )


@router.get("/{workflow_id}/versions")
async def versions(
    workflow_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
) -> dict:
    await workflows.get_workflow(session, member, workflow_id)
    rows = await session.scalars(
        select(WorkflowVersion)
        .where(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version_number.desc())
        .offset((page - 1) * 20)
        .limit(20)
    )
    total = await session.scalar(
        select(func.count())
        .select_from(WorkflowVersion)
        .where(WorkflowVersion.workflow_id == workflow_id)
    )
    return {
        "items": [VersionRead.model_validate(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": 20,
    }


@router.get("/{workflow_id}/versions/{version_id}", response_model=VersionRead)
async def version(
    workflow_id: UUID,
    version_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> WorkflowVersion:
    await workflows.get_workflow(session, member, workflow_id)
    row = await session.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.id == version_id, WorkflowVersion.workflow_id == workflow_id
        )
    )
    if row is None:
        raise HTTPException(404, "Published version not found.")
    return row
