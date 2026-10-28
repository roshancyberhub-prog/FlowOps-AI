from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import now
from app.leads.scoring import ScoringConfig, calculate_score
from app.models import Lead, ScoringProfile


async def get_profile(
    session: AsyncSession, organization_id: UUID, profile_id: UUID | None = None
) -> ScoringProfile:
    query = select(ScoringProfile).where(ScoringProfile.organization_id == organization_id)
    if profile_id:
        query = query.where(ScoringProfile.id == profile_id)
    profile = await session.scalar(query.order_by(ScoringProfile.version_number.desc()).limit(1))
    if profile is None:
        raise HTTPException(404, "Scoring profile not found.")
    return profile


def score_stored_lead(lead: Lead, profile: ScoringProfile) -> None:
    data = {
        key: getattr(lead, key)
        for key in (
            "job_title",
            "industry",
            "company_size",
            "email",
            "website",
            "company",
            "country",
        )
    }
    result = calculate_score(data, ScoringConfig.model_validate(profile.configuration))
    lead.score = result.score
    lead.score_reasons = result.reasons
    lead.score_profile_id = profile.id
    lead.score_profile_version = profile.version_number
    lead.scored_at = now()
