import asyncio
import copy
import logging
import time
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.base import now
from app.execution.dispatch import enqueue
from app.execution.errors import NodeFailure, classify_error, retry_delay, should_retry
from app.execution.handlers import handle_node
from app.execution.hashing import payload_hash
from app.execution.logic import next_node
from app.models import (
    ApprovalRequest,
    ExecutionStep,
    Membership,
    User,
    WorkflowExecution,
    WorkflowVersion,
)
from app.workflows.registry import REGISTRY
from app.workflows.schema import Graph

TERMINAL = {"succeeded", "failed", "cancelled"}


def finish(run: WorkflowExecution, status: str) -> None:
    run.status = status
    run.completed_at = now()
    run.lease_token = None
    run.lease_until = None


async def process_execution(factory: async_sessionmaker[AsyncSession], execution_id: UUID) -> None:
    settings = get_settings()
    token = uuid4()
    async with factory() as session:
        run = await session.scalar(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id).with_for_update()
        )
        if run is None or run.status in TERMINAL or run.status == "waiting_for_approval":
            return
        if run.cancel_requested:
            interrupted = await session.scalars(
                select(ExecutionStep).where(
                    ExecutionStep.execution_id == run.id, ExecutionStep.status == "running"
                )
            )
            for pending in interrupted:
                pending.completed_at = now()
                pending.uncertain = REGISTRY[pending.node_type].side_effect == "external"
                pending.status = "failed" if pending.uncertain else "cancelled"
                if pending.uncertain:
                    pending.error_code = run.error_code = "UNCERTAIN_EXTERNAL_RESULT"
                    pending.error_summary = run.error_summary = (
                        "The run was cancelled; reconcile the previous external attempt's outcome."
                    )
            finish(run, "cancelled")
            await session.commit()
            return
        if run.next_run_at > now() or run.lease_until and run.lease_until > now():
            return
        version = await session.get(WorkflowVersion, run.workflow_version_id)
        if version is None:
            return  # The foreign key guarantees this cannot occur in a valid database.
        graph = Graph.model_validate(version.graph_definition)
        node = next((node for node in graph.nodes if node.id == run.current_node_id), None)
        if node is None:
            finish(run, "succeeded")
            await session.commit()
            return
        spec = REGISTRY[node.type]
        previous = await session.scalar(
            select(ExecutionStep)
            .where(
                ExecutionStep.execution_id == run.id,
                ExecutionStep.node_id == node.id,
                ExecutionStep.status == "running",
            )
            .order_by(ExecutionStep.attempt_number.desc())
            .limit(1)
        )
        if previous:
            previous.status = "failed"
            previous.completed_at = now()
            previous.error_code = "WORKER_INTERRUPTED"
            previous.error_summary = "The worker stopped before recording this step's result."
            previous.retryable = spec.side_effect != "external"
            previous.uncertain = spec.side_effect == "external"
            if previous.uncertain:
                run.error_code = "UNCERTAIN_EXTERNAL_RESULT"
                run.error_summary = "Reconcile the previous external attempt before any new send."
                run.dead_letter = True
                finish(run, "failed")
                await session.commit()
                return
        if run.node_attempt >= settings.max_step_attempts:
            run.error_code = "ATTEMPTS_EXHAUSTED"
            run.error_summary = "The node exhausted its attempt budget after worker interruptions."
            run.dead_letter = True
            finish(run, "failed")
            await session.commit()
            return
        run.status = "running"
        run.started_at = run.started_at or now()
        run.lease_token = token
        run.lease_until = now() + timedelta(seconds=180)
        run.node_attempt += 1
        attempt = await session.scalar(
            select(func.max(ExecutionStep.attempt_number)).where(
                ExecutionStep.execution_id == run.id, ExecutionStep.node_id == node.id
            )
        )
        intent = ExecutionStep(
            execution_id=run.id,
            node_id=node.id,
            node_type=node.type,
            attempt_number=(attempt or 0) + 1,
            input_summary={"mode": run.mode, "lead_id": run.context.get("lead_id")},
        )
        session.add(intent)
        await session.flush()
        step_id = intent.id
        await session.commit()  # Persist intent before any external action.

    async with factory() as session:
        run = await session.scalar(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id).with_for_update()
        )
        if run is None or run.lease_token != token:
            return
        step = await session.get(ExecutionStep, step_id)
        assert step is not None
        if run.cancel_requested:
            step.status = "cancelled"
            step.completed_at = now()
            finish(run, "cancelled")
            await session.commit()
            return
        run.error_code = run.error_summary = None
        started = time.monotonic()
        context = copy.deepcopy(run.context)
        try:
            if run.active_duration_ms >= settings.execution_max_active_seconds * 1000:
                raise NodeFailure("EXECUTION_TIMEOUT", "The run exhausted its active time budget.")
            member = await session.scalar(
                select(Membership).where(
                    Membership.organization_id == run.organization_id,
                    Membership.user_id == run.requested_by,
                )
            )
            user = await session.get(User, run.requested_by)
            if (
                member is None
                or user is None
                or not user.is_active
                or member.role not in spec.roles
            ):
                raise NodeFailure(
                    "PERMISSION_REVOKED", "The run's user no longer has permission for this node."
                )
            async with session.begin_nested():
                async with asyncio.timeout(
                    min(
                        spec.timeout_seconds,
                        settings.execution_max_active_seconds - run.active_duration_ms / 1000,
                    )
                ):
                    outcome = await handle_node(session, run, node, context)
                step.output_summary = outcome.output
                if outcome.approval is not None:
                    approval = ApprovalRequest(
                        organization_id=run.organization_id,
                        execution_id=run.id,
                        execution_step_id=step.id,
                        node_id=node.id,
                        kind=outcome.approval["kind"],
                        payload=outcome.approval,
                        payload_hash=payload_hash(outcome.approval),
                        expires_at=now() + timedelta(hours=settings.approval_ttl_hours),
                    )
                    session.add(approval)
                    step.status = "waiting_for_approval"
                    run.status = "waiting_for_approval"
                else:
                    step.status = "succeeded"
                    step.completed_at = now()
                    run.current_node_id = next_node(graph, node.id, outcome.handle)
                    run.node_attempt = 0
                    if run.current_node_id is None:
                        finish(run, "succeeded")
                    else:
                        run.status = "queued"
                        enqueue(session, run, now() + timedelta(seconds=outcome.delay_seconds))
                run.context = context
        except Exception as exc:
            # Savepoint rollback can expire ORM state changed by a failed handler.
            await session.refresh(run)
            await session.refresh(step)
            failure = classify_error(exc, spec.side_effect)
            step.status = "failed"
            step.completed_at = now()
            step.error_code = run.error_code = failure.code
            step.error_summary = run.error_summary = failure.summary
            step.error_frames = list(failure.frames)
            step.retryable = failure.retryable
            step.uncertain = failure.uncertain
            if should_retry(failure, run.node_attempt, settings.max_step_attempts):
                run.status = "retrying"
                enqueue(session, run, now() + timedelta(seconds=retry_delay(run.node_attempt)))
            else:
                run.dead_letter = True
                finish(run, "failed")
        duration = int((time.monotonic() - started) * 1000)
        step.duration_ms = duration
        run.active_duration_ms += duration
        run.lease_token = None
        run.lease_until = None
        await session.commit()
        logging.getLogger("flowops.execution").info(
            "step_completed",
            extra={
                "execution_id": str(run.id),
                "request_id": run.correlation_id,
                "node_id": node.id,
                "node_type": node.type,
                "attempt": step.attempt_number,
                "step_status": step.status,
                "duration_ms": duration,
                "error_code": step.error_code,
            },
        )
