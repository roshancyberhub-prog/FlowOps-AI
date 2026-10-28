from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Lead, Membership, Organization, ScoringProfile
from app.schemas.leads import LeadRead
from app.schemas.scoring import ProfileCreate, ProfileRead, ScoreRequest
from app.security.permissions import ADMIN_ROLES, WRITE_ROLES, membership, require_role
from app.services.leads import audit, get_lead
from app.services.scoring import get_profile, score_stored_lead

router = APIRouter(tags=["lead scoring"])


@router.get("/scoring-profiles/current", response_model=ProfileRead)
async def current_profile(
    member: Membership = Depends(membership), session: AsyncSession = Depends(get_session)
) -> ScoringProfile:
    return await get_profile(session, member.organization_id)


@router.get("/scoring-profiles")
async def profiles(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
) -> dict:
    query = select(ScoringProfile).where(ScoringProfile.organization_id == member.organization_id)
    rows = await session.scalars(
        query.order_by(ScoringProfile.version_number.desc()).offset((page - 1) * 25).limit(25)
    )
    total = await session.scalar(
        select(func.count())
        .select_from(ScoringProfile)
        .where(ScoringProfile.organization_id == member.organization_id)
    )
    return {
        "items": [ProfileRead.model_validate(row) for row in rows],
        "total": total or 0,
        "page": page,
        "page_size": 25,
    }


@router.post("/scoring-profiles", response_model=ProfileRead, status_code=201)
async def create_profile(
    data: ProfileCreate,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> ScoringProfile:
    require_role(member, ADMIN_ROLES)
    await session.scalar(
        select(Organization).where(Organization.id == member.organization_id).with_for_update()
    )
    latest = await get_profile(session, member.organization_id)
    profile = ScoringProfile(
        organization_id=member.organization_id,
        created_by=member.user_id,
        version_number=latest.version_number + 1,
        name=data.name,
        configuration=data.configuration.model_dump(mode="json"),
    )
    session.add(profile)
    await session.flush()
    audit(session, member, "scoring_profile.created", profile.id, request.state.request_id)
    await session.commit()
    return profile


@router.post("/leads/{lead_id}/score", response_model=LeadRead)
async def score_lead(
    lead_id: UUID,
    data: ScoreRequest,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Lead:
    require_role(member, WRITE_ROLES)
    lead = await get_lead(session, member.organization_id, lead_id)
    profile = await get_profile(session, member.organization_id, data.profile_id)
    # Lock the lead so score, profile metadata and reasons remain consistent.
    await session.refresh(lead, with_for_update=True)
    if lead.status == "archived":
        raise HTTPException(409, "Restore this lead before scoring it.")
    score_stored_lead(lead, profile)
    audit(session, member, "lead.scored", lead.id, request.state.request_id)
    await session.commit()
    return lead
