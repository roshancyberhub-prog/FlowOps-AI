from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Membership, Workflow, WorkflowVersion
from app.schemas.workflows import WorkflowCreate, WorkflowPatch
from app.services.leads import audit
from app.workflows.graph import validate_graph
from app.workflows.registry import REGISTRY
from app.workflows.schema import Graph


async def get_workflow(
    session: AsyncSession,
    member: Membership,
    workflow_id: UUID,
    lock: bool = False,
) -> Workflow:
    query = select(Workflow).where(
        Workflow.id == workflow_id, Workflow.organization_id == member.organization_id
    )
    if lock:
        query = query.with_for_update()
    workflow = await session.scalar(query)
    if workflow is None:
        raise HTTPException(404, "Workflow not found.")
    return workflow


def check_revision(workflow: Workflow, expected: int) -> None:
    if workflow.revision != expected:
        raise HTTPException(409, "This workflow changed. Reload it before saving or publishing.")


async def create_workflow(
    session: AsyncSession,
    member: Membership,
    data: WorkflowCreate,
    request_id: str,
) -> Workflow:
    workflow = Workflow(
        organization_id=member.organization_id,
        created_by=member.user_id,
        name=data.name,
        description=data.description,
        draft_graph=data.graph.model_dump(mode="json", by_alias=True),
    )
    session.add(workflow)
    await session.flush()
    audit(session, member, "workflow.created", workflow.id, request_id)
    await session.commit()
    return workflow


async def update_workflow(
    session: AsyncSession,
    member: Membership,
    workflow_id: UUID,
    data: WorkflowPatch,
    request_id: str,
) -> Workflow:
    workflow = await get_workflow(session, member, workflow_id, lock=True)
    check_revision(workflow, data.expected_revision)
    if workflow.status == "archived":
        raise HTTPException(409, "Duplicate an archived workflow to edit it.")
    if data.name is not None:
        workflow.name = data.name.strip()
    if data.description is not None:
        workflow.description = data.description
    if data.graph is not None:
        workflow.draft_graph = data.graph.model_dump(mode="json", by_alias=True)
    workflow.revision += 1
    audit(session, member, "workflow.draft_saved", workflow.id, request_id)
    await session.commit()
    return workflow


async def publish_workflow(
    session: AsyncSession,
    member: Membership,
    workflow_id: UUID,
    expected: int,
    request_id: str,
) -> Workflow:
    workflow = await get_workflow(session, member, workflow_id, lock=True)
    check_revision(workflow, expected)
    if workflow.status == "archived":
        raise HTTPException(409, "Archived workflows cannot be published.")
    result = validate_graph(workflow.draft_graph, member.role)
    if not result.valid:
        raise HTTPException(
            422,
            detail={
                "code": "WORKFLOW_VALIDATION_FAILED",
                "message": "Fix the workflow validation errors before publishing.",
                "details": [issue.model_dump() for issue in result.errors],
            },
        )
    graph = Graph.model_validate(workflow.draft_graph)
    for node in graph.nodes:
        node.config = REGISTRY[node.type].config.model_validate(node.config).model_dump(mode="json")
    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=workflow.version_number + 1,
        graph_definition=graph.model_dump(mode="json", by_alias=True),
        created_by=member.user_id,
    )
    session.add(version)
    await session.flush()
    workflow.current_version_id = version.id
    workflow.version_number = version.version_number
    workflow.status = "active"
    workflow.revision += 1
    audit(session, member, "workflow.published", workflow.id, request_id)
    await session.commit()
    return workflow


async def transition(
    session: AsyncSession,
    member: Membership,
    workflow_id: UUID,
    target: str,
    expected: int,
    request_id: str,
) -> Workflow:
    workflow = await get_workflow(session, member, workflow_id, lock=True)
    check_revision(workflow, expected)
    allowed = {
        "paused": {"active"},
        "active": {"paused"},
        "archived": {"draft", "active", "paused"},
    }
    if workflow.status not in allowed[target]:
        raise HTTPException(409, f"Cannot change this workflow from {workflow.status} to {target}.")
    workflow.status = target
    workflow.revision += 1
    audit(session, member, f"workflow.{target}", workflow.id, request_id)
    await session.commit()
    return workflow
