from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import now
from app.execution.dispatch import enqueue
from app.execution.engine import TERMINAL, finish
from app.execution.hashing import payload_hash
from app.execution.logic import next_node
from app.models import (
    ApprovalRequest,
    ExecutionStep,
    Membership,
    WorkflowExecution,
    WorkflowVersion,
)
from app.schemas.executions import ApprovalDecision
from app.services.executions import get_execution
from app.services.leads import audit
from app.workflows.schema import Graph


async def cancel_execution(
    session: AsyncSession, member: Membership, run_id: UUID, request_id: str
) -> WorkflowExecution:
    run = await get_execution(session, member, run_id, lock=True)
    if run.status in TERMINAL:
        raise HTTPException(409, "This run has already ended.")
    run.cancel_requested = True
    # An in-flight worker owns a lease and observes cancellation at its next boundary.
    if run.lease_token is None:
        finish(run, "cancelled")
        approvals = await session.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.execution_id == run.id, ApprovalRequest.status == "pending")
            .with_for_update()
        )
        for approval in approvals:
            approval.status = "cancelled"
            approval.decided_at = now()
            approval.decided_by = member.user_id
            step = await session.get(ExecutionStep, approval.execution_step_id)
            if step:
                step.status = "cancelled"
                step.completed_at = now()
    audit(session, member, "execution.cancelled", run.id, request_id)
    await session.commit()
    return run


async def retry_execution(
    session: AsyncSession, member: Membership, run_id: UUID, request_id: str
) -> WorkflowExecution:
    run = await get_execution(session, member, run_id, lock=True)
    step = await session.scalar(
        select(ExecutionStep)
        .where(ExecutionStep.execution_id == run.id)
        .order_by(ExecutionStep.started_at.desc(), ExecutionStep.attempt_number.desc())
        .limit(1)
    )
    if run.status != "failed" or step is None or not step.retryable or step.uncertain:
        raise HTTPException(409, "This failure is not eligible for a safe retry.")
    if run.manual_retry_count >= 5:
        raise HTTPException(409, "This run has reached its manual retry limit.")
    run.manual_retry_count += 1
    run.node_attempt = 0
    run.dead_letter = False
    run.error_code = run.error_summary = None
    run.completed_at = None
    run.status = "queued"
    enqueue(session, run)
    audit(session, member, "execution.retried", run.id, request_id)
    await session.commit()
    return run


async def decide_approval(
    session: AsyncSession,
    member: Membership,
    approval_id: UUID,
    decision: str,
    data: ApprovalDecision,
    request_id: str,
) -> ApprovalRequest:
    initial = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == member.organization_id,
        )
    )
    if initial is None:
        raise HTTPException(404, "Approval not found.")
    # Every control operation locks the execution first, then its approval.
    run = await get_execution(session, member, initial.execution_id, lock=True)
    approval = await session.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.id == approval_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert approval is not None
    if approval.status != "pending" or run.status != "waiting_for_approval":
        raise HTTPException(409, "This approval is no longer pending.")
    if approval.expires_at <= now():
        approval.status = "expired"
        approval.decided_at = now()
        step = await session.get(ExecutionStep, approval.execution_step_id)
        if step:
            step.status = "expired"
            step.completed_at = now()
        finish(run, "cancelled")
        await session.commit()
        raise HTTPException(409, "This approval has expired.")
    if (
        data.revision != approval.revision
        or data.payload_hash != approval.payload_hash
        or payload_hash(approval.payload) != approval.payload_hash
    ):
        raise HTTPException(409, "The approval changed. Reload and review the current request.")
    approval.status = decision
    approval.decided_by = member.user_id
    approval.decided_at = now()
    approval.decision_comment = data.comment
    step = await session.get(ExecutionStep, approval.execution_step_id)
    assert step is not None
    step.completed_at = now()
    step.status = "succeeded" if decision == "approved" else "rejected"
    if decision == "rejected":
        finish(run, "cancelled")
    else:
        version = await session.get(WorkflowVersion, run.workflow_version_id)
        assert version is not None
        graph = Graph.model_validate(version.graph_definition)
        context = dict(run.context)
        context["approval"] = {
            "id": str(approval.id),
            "payload_hash": approval.payload_hash,
            "kind": approval.kind,
            "revision": approval.revision,
        }
        run.context = context
        run.current_node_id = next_node(graph, approval.node_id)
        run.node_attempt = 0
        if run.current_node_id:
            run.status = "queued"
            enqueue(session, run)
        else:
            finish(run, "succeeded")
    audit(session, member, f"approval.{decision}", approval.id, request_id)
    await session.commit()
    return approval
