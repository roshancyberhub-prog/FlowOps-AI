from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    lead_id: UUID | None
    execution_id: UUID
    recipient: str
    subject: str
    body: str
    qualification: dict
    provided_facts: dict
    ai_metadata: dict
    revision: int
    status: str
    execution_status: str = ""
    created_at: datetime
    updated_at: datetime
    last_edited_by: UUID | None


class DraftEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)


class DraftRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_id: UUID
    workflow_version_id: UUID | None = None
    mode: str = Field(default="test", pattern=r"^(test|live)$")


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    execution_id: UUID
    draft_id: UUID
    approval_id: UUID
    recipient: str
    provider: str
    provider_message_id: str
    status: str
    payload_hash: str
    delivery_metadata: dict
    created_at: datetime
