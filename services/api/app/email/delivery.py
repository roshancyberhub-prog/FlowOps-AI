from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.review import reviewed_draft
from app.ai.schemas import DraftContent
from app.email.providers import get_email_provider
from app.execution.errors import NodeFailure
from app.models import ApprovalRequest, EmailDelivery, Lead, Membership, User, WorkflowExecution


async def deliver_approved_email(
    session: AsyncSession, run: WorkflowExecution, node_id: str, context: dict
) -> EmailDelivery:
    existing = await session.scalar(
        select(EmailDelivery).where(
            EmailDelivery.execution_id == run.id,
            EmailDelivery.node_id == node_id,
            EmailDelivery.organization_id == run.organization_id,
        )
    )
    if existing:
        return existing
    authority = context.get("email_approval", {})
    try:
        approval_id = UUID(authority["id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise NodeFailure(
            "APPROVAL_REQUIRED", "A current email approval is required before sending."
        ) from exc
    approval = await session.scalar(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == run.organization_id,
            ApprovalRequest.execution_id == run.id,
        )
        .with_for_update()
    )
    if (
        approval is None
        or approval.status != "approved"
        or authority.get("kind") != "email"
        or authority.get("payload_hash") != approval.payload_hash
        or authority.get("revision") != approval.revision
    ):
        raise NodeFailure(
            "APPROVAL_REQUIRED", "A current email approval is required before sending."
        )
    approver = await session.scalar(
        select(Membership).where(
            Membership.organization_id == run.organization_id,
            Membership.user_id == approval.decided_by,
        )
    )
    approver_user = await session.get(User, approval.decided_by) if approval.decided_by else None
    if (
        approver is None
        or approver.role not in {"owner", "admin"}
        or approver_user is None
        or not approver_user.is_active
    ):
        raise NodeFailure(
            "APPROVER_NO_LONGER_AUTHORIZED",
            "The approving user no longer has permission. Start a new reviewed run.",
        )
    try:
        draft = await reviewed_draft(session, run, approval, "approved")
    except HTTPException as exc:
        raise NodeFailure(
            "APPROVAL_INVALID", "The approved draft no longer matches this send request."
        ) from exc
    if run.mode == "live":
        lead = await session.scalar(
            select(Lead)
            .where(Lead.id == draft.lead_id, Lead.organization_id == run.organization_id)
            .with_for_update()
        )
        if lead is None or lead.status == "archived" or lead.email != draft.recipient:
            raise NodeFailure(
                "RECIPIENT_CHANGED",
                "The stored recipient changed or is unavailable. Start a new reviewed run.",
            )
        fields = ("name", "company", "job_title", "industry", "company_size", "website", "country")
        if any(getattr(lead, field) != draft.provided_facts.get(field) for field in fields):
            raise NodeFailure(
                "LEAD_CHANGED",
                "The provided lead facts changed after drafting. Start a new reviewed run.",
            )
    provider = get_email_provider(run.mode)
    key = f"{run.id}:{node_id}"
    result = await provider.send(
        draft.recipient, DraftContent(subject=draft.subject, body=draft.body), key
    )
    delivery = EmailDelivery(
        organization_id=run.organization_id,
        execution_id=run.id,
        node_id=node_id,
        draft_id=draft.id,
        approval_id=approval.id,
        recipient=draft.recipient,
        idempotency_key=key,
        payload_hash=approval.payload_hash,
        provider=result.provider,
        provider_message_id=result.message_id,
        status=result.status,
        delivery_metadata={
            "simulated": result.simulated,
            "external_message_sent": not result.simulated,
        },
    )
    draft.status = "simulated" if result.simulated else "sent"
    session.add(delivery)
    await session.flush()
    return delivery
