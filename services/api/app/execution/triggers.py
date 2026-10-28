from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import now
from app.execution.dispatch import enqueue
from app.execution.hashing import payload_hash
from app.models import AuditLog, Lead, Workflow, WorkflowExecution, WorkflowVersion
from app.schemas.leads import LeadRead
from app.workflows.registry import Schedule
from app.workflows.schema import Graph


def scheduled_time(graph: Graph) -> datetime | None:
    node = next((n for n in graph.nodes if n.type == "trigger.scheduled"), None)
    return (
        now() + timedelta(minutes=Schedule.model_validate(node.config).interval_minutes)
        if node
        else None
    )


async def create_automatic_run(
    session: AsyncSession,
    workflow: Workflow,
    version: WorkflowVersion,
    trigger_type: str,
    key: str,
    context: dict,
    correlation_id: str,
) -> WorkflowExecution:
    graph = Graph.model_validate(version.graph_definition)
    trigger = next(node for node in graph.nodes if node.type == trigger_type)
    run = WorkflowExecution(
        organization_id=workflow.organization_id,
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        workflow_name=workflow.name,
        version_number=version.version_number,
        requested_by=version.created_by,
        trigger_type=trigger_type.removeprefix("trigger."),
        correlation_id=correlation_id,
        mode="live",
        idempotency_key=key,
        input_hash=payload_hash({"key": key}),
        context=context,
        input_summary={"lead_id": context.get("lead_id"), "automatic": True},
        current_node_id=trigger.id,
    )
    session.add(run)
    await session.flush()
    enqueue(session, run)
    session.add(
        AuditLog(
            organization_id=run.organization_id,
            actor_user_id=version.created_by,
            action="execution.triggered",
            resource_id=str(run.id),
            correlation_id=correlation_id,
        )
    )
    return run


async def lead_created(session: AsyncSession, lead: Lead, correlation_id: str) -> None:
    rows = await session.execute(
        select(Workflow, WorkflowVersion)
        .join(WorkflowVersion, Workflow.current_version_id == WorkflowVersion.id)
        .where(Workflow.organization_id == lead.organization_id, Workflow.status == "active")
    )
    for workflow, version in rows:
        graph = Graph.model_validate(version.graph_definition)
        if any(node.type == "trigger.lead_created" for node in graph.nodes):
            await create_automatic_run(
                session,
                workflow,
                version,
                "trigger.lead_created",
                f"lead-created:{lead.id}:{version.id}",
                {
                    "lead_id": str(lead.id),
                    "lead": LeadRead.model_validate(lead).model_dump(mode="json"),
                },
                correlation_id,
            )


async def schedule_due(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as session:
        workflows = await session.scalars(
            select(Workflow)
            .where(Workflow.status == "active", Workflow.scheduled_next_run_at <= now())
            .with_for_update(skip_locked=True)
            .limit(100)
        )
        for workflow in workflows:
            version = await session.get(WorkflowVersion, workflow.current_version_id)
            if version is None:
                continue
            slot = workflow.scheduled_next_run_at
            assert slot is not None
            graph = Graph.model_validate(version.graph_definition)
            workflow.scheduled_next_run_at = scheduled_time(graph)
            if workflow.scheduled_next_run_at is None:
                continue
            # One coalesced run after downtime, rather than replaying every missed interval.
            await create_automatic_run(
                session,
                workflow,
                version,
                "trigger.scheduled",
                f"scheduled:{version.id}:{slot.isoformat()}",
                {},
                str(uuid4()),
            )
        await session.commit()
