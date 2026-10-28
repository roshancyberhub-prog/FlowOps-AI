import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.execution.dispatch import enqueue
from app.models import Membership, WorkflowExecution, WorkflowVersion
from app.schemas.executions import RunRequest
from app.schemas.leads import LeadRead
from app.services.leads import audit, get_lead
from app.services.workflows import get_workflow
from app.workflows.graph import validate_graph
from app.workflows.schema import Graph


def payload_hash(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


async def get_execution(
    session: AsyncSession,
    member: Membership,
    execution_id: UUID,
    lock: bool = False,
) -> WorkflowExecution:
    query = select(WorkflowExecution).where(
        WorkflowExecution.id == execution_id,
        WorkflowExecution.organization_id == member.organization_id,
    )
    if lock:
        query = query.with_for_update()
    execution = await session.scalar(query)
    if execution is None:
        raise HTTPException(404, "Execution not found.")
    return execution


async def request_execution(
    session: AsyncSession,
    member: Membership,
    workflow_id: UUID,
    data: RunRequest,
    idempotency_key: str,
    request_id: str,
    mode: str,
) -> tuple[WorkflowExecution, bool]:
    workflow = await get_workflow(session, member, workflow_id)
    organization_id = member.organization_id
    digest = payload_hash(
        {"workflow_id": str(workflow_id), "input": data.model_dump(mode="json"), "mode": mode}
    )
    existing = await session.scalar(
        select(WorkflowExecution).where(
            WorkflowExecution.organization_id == organization_id,
            WorkflowExecution.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.input_hash != digest:
            raise HTTPException(409, "This idempotency key was already used for a different run.")
        return existing, False
    if workflow.status == "archived" or workflow.current_version_id is None:
        raise HTTPException(409, "Publish this workflow before running it.")
    version_id = data.workflow_version_id or workflow.current_version_id
    version = await session.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.id == version_id, WorkflowVersion.workflow_id == workflow.id
        )
    )
    if version is None:
        raise HTTPException(404, "Published version not found.")
    validation = validate_graph(version.graph_definition, member.role)
    if not validation.valid:
        raise HTTPException(403, "Your role cannot run this workflow's configured actions.")
    context: dict = {}
    if data.lead_id:
        lead = await get_lead(session, member.organization_id, data.lead_id)
        if lead.status == "archived":
            raise HTTPException(409, "Restore the lead before processing it.")
        context = {
            "lead_id": str(lead.id),
            "lead": LeadRead.model_validate(lead).model_dump(mode="json"),
        }
    elif data.sample_lead:
        context = {"lead": data.sample_lead.model_dump(mode="json")}
    graph = Graph.model_validate(version.graph_definition)
    trigger = next(node for node in graph.nodes if node.type.startswith("trigger."))
    execution = WorkflowExecution(
        organization_id=member.organization_id,
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        workflow_name=workflow.name,
        version_number=version.version_number,
        requested_by=member.user_id,
        trigger_type="manual",
        correlation_id=request_id,
        mode=mode,
        idempotency_key=idempotency_key,
        input_hash=digest,
        context=context,
        input_summary={
            "lead_id": str(data.lead_id) if data.lead_id else None,
            "sample": data.sample_lead is not None,
        },
        current_node_id=trigger.id,
    )
    session.add(execution)
    try:
        await session.flush()
        enqueue(session, execution)
        audit(session, member, "execution.requested", execution.id, request_id)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if "uq_execution_idempotency" not in str(exc.orig):
            raise
        existing = await session.scalar(
            select(WorkflowExecution).where(
                WorkflowExecution.organization_id == organization_id,
                WorkflowExecution.idempotency_key == idempotency_key,
            )
        )
        if existing is None or existing.input_hash != digest:
            raise HTTPException(409, "Conflicting execution request.") from exc
        return existing, False
    return execution, True
