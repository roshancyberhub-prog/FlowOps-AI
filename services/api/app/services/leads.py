from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Lead, Membership
from app.schemas.leads import LeadCreate, LeadPage, LeadPatch, LeadRead


def audit(
    session: AsyncSession, member: Membership, action: str, resource: UUID, request_id: str
) -> None:
    session.add(
        AuditLog(
            organization_id=member.organization_id,
            actor_user_id=member.user_id,
            action=action,
            resource_id=str(resource),
            correlation_id=request_id,
        )
    )


async def get_lead(session: AsyncSession, organization_id: UUID, lead_id: UUID) -> Lead:
    lead = await session.scalar(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.organization_id == organization_id,
        )
    )
    if lead is None:
        raise HTTPException(404, "Lead not found.")
    return lead


async def list_leads(
    session: AsyncSession,
    organization_id: UUID,
    search: str,
    status: str | None,
    page: int,
    page_size: int,
) -> LeadPage:
    conditions = [Lead.organization_id == organization_id]
    if status:
        conditions.append(Lead.status == status)
    else:
        conditions.append(Lead.status != "archived")
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(
            or_(
                Lead.name.ilike(f"%{escaped}%", escape="\\"),
                Lead.email.ilike(f"%{escaped}%", escape="\\"),
                Lead.company.ilike(f"%{escaped}%", escape="\\"),
            )
        )
    total = await session.scalar(select(func.count()).select_from(Lead).where(*conditions))
    rows = await session.scalars(
        select(Lead)
        .where(*conditions)
        .order_by(Lead.created_at.desc(), Lead.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return LeadPage(
        items=[LeadRead.model_validate(row) for row in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def save_lead(
    session: AsyncSession,
    member: Membership,
    data: LeadCreate | LeadPatch,
    request_id: str,
    lead_id: UUID | None = None,
) -> Lead:
    if lead_id:
        lead = await get_lead(session, member.organization_id, lead_id)
        for key, value in data.model_dump(mode="json", exclude_unset=True).items():
            setattr(lead, key, value)
    else:
        lead = Lead(organization_id=member.organization_id, **data.model_dump(mode="json"))
        session.add(lead)
    try:
        await session.flush()
        audit(session, member, "lead.updated" if lead_id else "lead.created", lead.id, request_id)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if "uq_lead_organization_email" in str(exc.orig):
            raise HTTPException(
                409, "A lead with this email already exists in this workspace."
            ) from exc
        raise
    return lead
