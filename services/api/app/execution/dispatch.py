from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import now
from app.models import OutboxEntry, WorkflowExecution


def enqueue(
    session: AsyncSession, execution: WorkflowExecution, available_at: datetime | None = None
) -> None:
    execution.dispatch_generation += 1
    execution.next_run_at = available_at or now()
    session.add(
        OutboxEntry(
            execution_id=execution.id,
            dispatch_key=f"{execution.id}:{execution.dispatch_generation}",
            available_at=execution.next_run_at,
        )
    )
