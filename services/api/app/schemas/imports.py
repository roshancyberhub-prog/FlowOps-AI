from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    filename: str
    column_mapping: dict[str, str]
    total_rows: int
    processed_rows: int
    inserted_rows: int
    invalid_rows: int
    duplicate_rows: int
    failure_count: int
    error_code: str | None
    error_summary: str | None
    correlation_id: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ImportRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    row_number: int
    status: str
    email: str | None
    input_values: dict
    errors: list[dict]
    lead_id: UUID | None
