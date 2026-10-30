from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.leads.scoring import ScoringConfig
from app.models import AuditLog, Membership, Organization, ScoringProfile, User
from app.security.auth import UserRead, current_user
from app.security.permissions import ADMIN_ROLES, membership, require_role
from app.services.leads import audit

router = APIRouter(tags=["organizations"])


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    role: str


class MemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    role: Literal["admin", "member", "viewer"] = "member"


class MemberRole(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["admin", "member", "viewer"]


class MemberRead(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    display_name: str
    role: str


@router.get("/users/me", response_model=UserRead)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/organizations", response_model=list[OrganizationRead])
async def organizations(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[OrganizationRead]:
    rows = await session.execute(
        select(Organization, Membership.role)
        .join(
            Membership,
            Membership.organization_id == Organization.id,
        )
        .where(Membership.user_id == user.id)
        .order_by(Organization.created_at)
    )
    return [OrganizationRead(id=org.id, name=org.name, role=role) for org, role in rows]


@router.post("/organizations", response_model=OrganizationRead, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    org = Organization(name=data.name, slug=str(uuid4()))
    session.add(org)
    await session.flush()
    session.add(
        ScoringProfile(
            organization_id=org.id,
            version_number=1,
            name="Baseline ICP",
            configuration=ScoringConfig().model_dump(mode="json"),
            created_by=user.id,
        )
    )
    member = Membership(organization_id=org.id, user_id=user.id, role="owner")
    session.add(member)
    audit(session, member, "organization.created", org.id, request.state.request_id)
    await session.commit()
    return OrganizationRead(id=org.id, name=org.name, role="owner")


@router.get("/organizations/{organization_id}/members", response_model=list[MemberRead])
async def members(
    organization_id: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> list[MemberRead]:
    if organization_id != member.organization_id:
        raise HTTPException(404, "Workspace not found.")
    rows = await session.execute(
        select(Membership, User)
        .join(User, User.__table__.c.id == Membership.user_id)
        .where(Membership.organization_id == organization_id)
        .order_by(Membership.created_at)
    )
    return [
        MemberRead(id=m.id, user_id=u.id, email=u.email, display_name=u.display_name, role=m.role)
        for m, u in rows
    ]


@router.post("/organizations/{organization_id}/members", status_code=201)
async def add_member(
    organization_id: UUID,
    data: MemberCreate,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    require_role(member, ADMIN_ROLES)
    if organization_id != member.organization_id:
        raise HTTPException(404, "Workspace not found.")
    if data.role == "admin" and member.role != "owner":
        raise HTTPException(403, "Only the owner may grant admin access.")
    user = await session.scalar(
        select(User).where(User.__table__.c.email == str(data.email).strip().lower())
    )
    if user is None:
        raise HTTPException(404, "Ask this person to register before adding them.")
    new_member = Membership(organization_id=organization_id, user_id=user.id, role=data.role)
    session.add(new_member)
    try:
        await session.flush()
        audit(session, member, "member.added", new_member.id, request.state.request_id)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "This user already belongs to the workspace.") from exc
    return {"id": str(new_member.id), "role": new_member.role}


@router.patch("/organizations/{organization_id}/members/{member_id}")
async def update_member(
    organization_id: UUID,
    member_id: UUID,
    data: MemberRole,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    require_role(member, ADMIN_ROLES)
    if organization_id != member.organization_id:
        raise HTTPException(404, "Workspace not found.")
    target = await session.scalar(
        select(Membership)
        .where(
            Membership.id == member_id,
            Membership.organization_id == organization_id,
        )
        .with_for_update()
    )
    if target is None:
        raise HTTPException(404, "Member not found.")
    if target.role == "owner" or (
        member.role != "owner" and (target.role == "admin" or data.role == "admin")
    ):
        raise HTTPException(403, "This role change requires the workspace owner.")
    target.role = data.role
    audit(session, member, "member.role_changed", target.id, request.state.request_id)
    await session.commit()
    return {"id": str(target.id), "role": target.role}


@router.get("/audit")
async def audit_history(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1, le=10000),
) -> list[dict]:
    require_role(member, ADMIN_ROLES)
    rows = await session.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == member.organization_id)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * 50)
        .limit(50)
    )
    return [
        {
            "id": str(row.id),
            "action": row.action,
            "resource_id": row.resource_id,
            "created_at": row.created_at.isoformat(),
            "correlation_id": row.correlation_id,
        }
        for row in rows
    ]
