from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.leads import LeadCreate


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lead_id: UUID | None = None
    sample_lead: LeadCreate | None = None
    workflow_version_id: UUID | None = None

    @model_validator(mode="after")
    def choose_one_lead_source(self) -> Self:
        if self.lead_id is not None and self.sample_lead is not None:
            raise ValueError("Choose a stored lead or sample lead, not both.")
        return self


ExecutionStatus = Literal[
    "queued", "running", "waiting_for_approval", "retrying", "succeeded", "failed", "cancelled"
]


class ExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    workflow_name: str
    version_number: int
    status: ExecutionStatus
    mode: str
    trigger_type: str
    input_summary: dict
    context: dict
    current_node_id: str | None
    node_attempt: int
    active_duration_ms: int
    cancel_requested: bool
    error_code: str | None
    error_summary: str | None
    dead_letter: bool
    correlation_id: str
    next_run_at: datetime
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ExecutionPage(BaseModel):
    items: list[ExecutionRead]
    total: int
    page: int
    page_size: int


class StepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    node_id: str
    node_type: str
    attempt_number: int
    status: str
    input_summary: dict
    output_summary: dict
    error_code: str | None
    error_summary: str | None
    error_frames: list[str]
    retryable: bool
    uncertain: bool
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
