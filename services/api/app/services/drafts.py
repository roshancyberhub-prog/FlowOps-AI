from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.drafting import draft_snapshot
from app.ai.schemas import DraftContent
from app.db.base import now
from app.execution.hashing import payload_hash
from app.models import ApprovalRequest, EmailDraft, Membership
from app.schemas.outreach import DraftEdit
from app.services.executions import get_execution
from app.services.leads import audit


async def get_draft(session: AsyncSession, member: Membership, draft_id: UUID) -> EmailDraft:
    draft = await session.scalar(
        select(EmailDraft).where(
            EmailDraft.id == draft_id, EmailDraft.organization_id == member.organization_id
        )
    )
    if draft is None:
        raise HTTPException(404, "Draft not found.")
    return draft


async def edit_draft(
    session: AsyncSession, member: Membership, draft_id: UUID, data: DraftEdit, request_id: str
) -> EmailDraft:
    draft = await get_draft(session, member, draft_id)
    run = await get_execution(session, member, draft.execution_id, lock=True)
    await session.refresh(draft, with_for_update=True)
    if (
        draft.status != "pending_review"
        or run.status in {"succeeded", "failed", "cancelled"}
        or run.context.get("draft", {}).get("id") != str(draft.id)
    ):
        raise HTTPException(
            409, "Only the current unapproved draft in an active run may be edited."
        )
    if data.expected_revision != draft.revision:
        raise HTTPException(409, "This draft changed. Reload its current version before editing.")
    try:
        content = DraftContent(subject=data.subject, body=data.body)
    except ValidationError as exc:
        raise HTTPException(
            422, "Use a nonempty body and a single-line subject without control characters."
        ) from exc
    pending = list(
        await session.scalars(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.execution_id == run.id,
                ApprovalRequest.status == "pending",
                ApprovalRequest.kind == "email",
            )
            .with_for_update()
        )
    )
    if any(approval.expires_at <= now() for approval in pending):
        raise HTTPException(409, "This review expired. Start a new run instead.")
    draft.subject, draft.body = content.subject, content.body
    draft.revision += 1
    draft.last_edited_by = member.user_id
    snapshot = draft_snapshot(draft)
    context = dict(run.context)
    context["draft"] = snapshot
    context.pop("approval", None)
    context.pop("email_approval", None)
    run.context = context
    for approval in pending:
        if approval.payload.get("draft", {}).get("id") == str(draft.id):
            approval.payload = {**approval.payload, "draft": snapshot}
            approval.payload_hash = payload_hash(approval.payload)
            approval.revision += 1
    audit(session, member, "draft.edited", draft.id, request_id)
    await session.commit()
    return draft
