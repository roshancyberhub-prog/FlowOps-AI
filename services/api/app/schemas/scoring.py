from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.leads.scoring import ScoringConfig


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(default="Baseline ICP", min_length=1, max_length=100)
    configuration: ScoringConfig = Field(default_factory=ScoringConfig)


class ProfileRead(ProfileCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version_number: int
    created_at: datetime


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: UUID | None = None
