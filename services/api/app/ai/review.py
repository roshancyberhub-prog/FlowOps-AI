from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.drafting import draft_snapshot
from app.db.base import now
from app.execution.hashing import payload_hash
from app.models import ApprovalRequest, EmailDraft, WorkflowExecution


async def reviewed_draft(
    session: AsyncSession, run: WorkflowExecution, approval: ApprovalRequest, required_status: str
) -> EmailDraft:
    snapshot = approval.payload.get("draft")
    if not isinstance(snapshot, dict):
        raise HTTPException(409, "This approval has no valid email draft.")
    try:
        draft_id = UUID(snapshot["id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, "This approval has no valid email draft.") from exc
    draft = await session.scalar(
        select(EmailDraft)
        .where(
            EmailDraft.id == draft_id,
            EmailDraft.execution_id == run.id,
            EmailDraft.organization_id == run.organization_id,
        )
        .with_for_update()
    )
    if (
        draft is None
        or draft.status != required_status
        or approval.kind != "email"
        or approval.execution_id != run.id
        or approval.organization_id != run.organization_id
        or approval.expires_at <= now()
        or approval.payload.get("mode") != run.mode
        or payload_hash(approval.payload) != approval.payload_hash
        or snapshot != draft_snapshot(draft)
        or run.context.get("draft", {}).get("id") != str(draft.id)
    ):
        raise HTTPException(
            409, "This draft or approval changed. Reload and review its current contents."
        )
    return draft
