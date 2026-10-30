from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Lead, Membership
from app.schemas.leads import LeadCreate, LeadPage, LeadPatch, LeadRead, LeadStatus
from app.security.permissions import WRITE_ROLES, membership, require_role
from app.services import leads

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadPage)
async def list_leads(
    search: str = Query(default="", max_length=200),
    status: LeadStatus | None = None,
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=25, ge=1, le=100),
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> LeadPage:
    return await leads.list_leads(session, member.organization_id, search, status, page, page_size)


@router.post("", response_model=LeadRead, status_code=201)
async def create_lead(
    data: LeadCreate,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Lead:
    require_role(member, WRITE_ROLES)
    return await leads.save_lead(session, member, data, request.state.request_id)


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(
    lead_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Lead:
    return await leads.get_lead(session, member.organization_id, lead_id)


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: UUID,
    data: LeadPatch,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Lead:
    require_role(member, WRITE_ROLES)
    return await leads.save_lead(session, member, data, request.state.request_id, lead_id)


@router.delete("/{lead_id}", status_code=204)
async def archive_lead(
    lead_id: UUID,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Response:
    require_role(member, WRITE_ROLES)
    await leads.save_lead(
        session, member, LeadPatch(status="archived"), request.state.request_id, lead_id
    )
    return Response(status_code=204)
