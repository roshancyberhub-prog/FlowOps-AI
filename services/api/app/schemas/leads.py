from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

LeadStatus = Literal["new", "qualified", "contacted", "won", "lost", "archived"]


class LeadFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    company: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=150)
    website: HttpUrl | None = None
    industry: str | None = Field(default=None, max_length=100)
    company_size: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=100)


class LeadCreate(LeadFields):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr = Field(max_length=320)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value


class LeadPatch(LeadFields):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    status: LeadStatus | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        for field in ("name", "email", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    name: str
    email: str
    company: str | None
    job_title: str | None
    website: str | None
    industry: str | None
    company_size: str | None
    country: str | None
    source: str | None
    status: str
    score: int
    score_reasons: list
    created_at: datetime
    updated_at: datetime


class LeadPage(BaseModel):
    items: list[LeadRead]
    total: int
    page: int
    page_size: int
