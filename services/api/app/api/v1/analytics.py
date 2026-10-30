from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import now
from app.db.session import get_session
from app.models import ApprovalRequest, Lead, Membership, Workflow, WorkflowExecution
from app.security.permissions import membership

router = APIRouter(tags=["analytics"])


@router.get("/analytics/overview")
async def overview(
    member: Membership = Depends(membership), session: AsyncSession = Depends(get_session)
) -> dict:
    timestamp = now()
    start = (timestamp - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    org = member.organization_id
    leads = await session.scalar(
        select(func.count())
        .select_from(Lead)
        .where(Lead.organization_id == org, Lead.status != "archived")
    )
    workflows = await session.scalar(
        select(func.count())
        .select_from(Workflow)
        .where(Workflow.organization_id == org, Workflow.status == "active")
    )
    approvals = await session.scalar(
        select(func.count())
        .select_from(ApprovalRequest)
        .where(
            ApprovalRequest.organization_id == org,
            ApprovalRequest.status == "pending",
            ApprovalRequest.expires_at > timestamp,
        )
    )
    runs = select(WorkflowExecution).where(
        WorkflowExecution.organization_id == org,
        WorkflowExecution.created_at >= start,
        WorkflowExecution.created_at <= timestamp,
    )
    count_rows = (
        await session.execute(
            select(WorkflowExecution.status, func.count())
            .where(
                WorkflowExecution.organization_id == org,
                WorkflowExecution.created_at >= start,
                WorkflowExecution.created_at <= timestamp,
            )
            .group_by(WorkflowExecution.status)
        )
    ).all()
    counts = {status: count for status, count in count_rows}
    succeeded, failed = counts.get("succeeded", 0), counts.get("failed", 0)
    day = cast(func.timezone("UTC", WorkflowExecution.created_at), Date)
    rows = (
        await session.execute(
            select(day, WorkflowExecution.status, func.count())
            .where(
                WorkflowExecution.organization_id == org,
                WorkflowExecution.created_at >= start,
                WorkflowExecution.created_at <= timestamp,
            )
            .group_by(day, WorkflowExecution.status)
        )
    ).all()
    buckets: dict[str, dict] = {}
    for index in range(7):
        date = (start + timedelta(days=index)).date().isoformat()
        buckets[date] = {"date": date, "succeeded": 0, "failed": 0, "other": 0}
    for date_value, status, count in rows:
        key = status if status in {"succeeded", "failed"} else "other"
        buckets[date_value.isoformat()][key] += count
    duration = await session.scalar(
        select(func.avg(WorkflowExecution.active_duration_ms)).where(
            WorkflowExecution.organization_id == org,
            WorkflowExecution.created_at >= start,
            WorkflowExecution.created_at <= timestamp,
            WorkflowExecution.status.in_(["succeeded", "failed"]),
        )
    )
    recent = await session.scalars(runs.order_by(WorkflowExecution.created_at.desc()).limit(5))
    return {
        "generated_at": timestamp,
        "period_start": start,
        "active_leads": leads or 0,
        "active_workflows": workflows or 0,
        "pending_approvals": approvals or 0,
        "executions": sum(counts.values()),
        "succeeded": succeeded,
        "failed": failed,
        "success_rate": round(succeeded / (succeeded + failed) * 100, 1)
        if succeeded + failed
        else None,
        "average_active_ms": round(float(duration), 1) if duration is not None else None,
        "daily": list(buckets.values()),
        "recent_executions": [
            {
                "id": r.id,
                "workflow_name": r.workflow_name,
                "status": r.status,
                "mode": r.mode,
                "created_at": r.created_at,
            }
            for r in recent
        ],
    }
