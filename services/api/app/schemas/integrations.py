from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.leads import LeadCreate
from app.workflows.schema import StrictModel


class GitHubConfig(StrictModel):
    owner: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
    repo: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")


class WebhookConfig(StrictModel):
    workflow_id: UUID | None = None
    destination: str | None = Field(default=None, max_length=2048)
    receiver_deduplicates: bool = False

    @field_validator("destination")
    @classmethod
    def https_only(cls, value: str | None) -> str | None:
        if value is None:
            return value
        import httpx

        try:
            url = httpx.URL(value)
        except httpx.InvalidURL as exc:
            raise ValueError("Use a valid HTTPS URL.") from exc
        if (
            url.scheme != "https"
            or not url.host
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.port not in {None, 443}
        ):
            raise ValueError("Use HTTPS port 443 without credentials, query strings or fragments.")
        return str(url)


class IntegrationCreate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    provider: Literal["github", "webhook"]
    configuration: dict


class IntegrationPatch(StrictModel):
    expected_revision: int = Field(ge=1)
    enabled: bool


class IntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    provider: str
    configuration: dict
    enabled: bool
    revision: int
    last_test_status: str
    last_test_at: datetime | None
    last_error: str | None
    last_result: dict
    created_at: datetime


class IncomingEvent(StrictModel):
    event_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9:_-]+$")
    lead: LeadCreate


class DeliveryCreate(StrictModel):
    execution_id: UUID | None = None
