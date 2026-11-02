from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, populate_by_name=True)


class Position(StrictModel):
    x: float = Field(default=0, ge=-100000, le=100000)
    y: float = Field(default=0, ge=-100000, le=100000)


class Node(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    type: str = Field(max_length=80)
    label: str | None = Field(default=None, max_length=80)
    config: dict = Field(default_factory=dict)
    position: Position = Field(default_factory=Position)


class Edge(StrictModel):
    id: str | None = Field(default=None, max_length=150)
    source: str = Field(max_length=64)
    target: str = Field(max_length=64)
    source_handle: str | None = Field(default=None, alias="sourceHandle", max_length=20)


class Graph(StrictModel):
    schema_version: Literal[1] = 1
    nodes: list[Node] = Field(default_factory=list, max_length=100)
    edges: list[Edge] = Field(default_factory=list, max_length=200)


class Issue(StrictModel):
    code: str
    message: str
    node_id: str | None = None


class ValidationResult(StrictModel):
    valid: bool
    errors: list[Issue]
    order: list[str]
