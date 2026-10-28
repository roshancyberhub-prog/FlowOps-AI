from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.workflows.schema import Graph
from app.workflows.templates import basic_graph


class WorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=1000)
    graph: Graph = Field(default_factory=basic_graph)


class Revision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_revision: int = Field(ge=1)


class WorkflowPatch(Revision):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    graph: Graph | None = None

    @model_validator(mode="after")
    def reject_null_updates(self) -> Self:
        for field in ("name", "description", "graph"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    status: Literal["draft", "active", "paused", "archived"]
    draft_graph: dict
    current_version_id: UUID | None
    version_number: int
    revision: int
    created_at: datetime
    updated_at: datetime


class WorkflowPage(BaseModel):
    items: list[WorkflowRead]
    total: int
    page: int
    page_size: int


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workflow_id: UUID
    version_number: int
    graph_definition: dict
    created_at: datetime
