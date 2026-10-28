from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Membership, User
from app.security.auth import current_user


async def membership(
    user: User = Depends(current_user),
    workspace_id: UUID = Header(alias="X-Organization-ID"),
    session: AsyncSession = Depends(get_session),
) -> Membership:
    result = await session.scalar(
        select(Membership).where(
            Membership.organization_id == workspace_id,
            Membership.user_id == user.id,
        )
    )
    if result is None:
        raise HTTPException(403, "Organization access denied.")
    return result


def require_role(member: Membership, allowed: set[str]) -> None:
    if member.role not in allowed:
        raise HTTPException(403, "Your workspace role does not permit this action.")


WRITE_ROLES = {"owner", "admin", "member"}
ADMIN_ROLES = {"owner", "admin"}
