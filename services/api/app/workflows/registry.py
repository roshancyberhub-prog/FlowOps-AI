import builtins
from dataclasses import dataclass
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.workflows.schema import StrictModel


class Empty(StrictModel):
    pass


class Schedule(StrictModel):
    interval_minutes: int = Field(default=60, ge=1, le=10080)


class Approval(StrictModel):
    kind: Literal["email", "continue"] = "email"
    message: str = Field(default="Review before continuing.", min_length=1, max_length=1000)


class Score(StrictModel):
    scoring_profile: str = Field(default="default", max_length=80)

    @field_validator("scoring_profile")
    @classmethod
    def known_profile_reference(cls, value: str) -> str:
        if value == "default":
            return value
        return str(UUID(value))


class Draft(StrictModel):
    value_proposition: str = Field(default="Help your team streamline operations.", max_length=1000)
    template: Literal["initial_follow_up"] = "initial_follow_up"


class Condition(StrictModel):
    field: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z_][a-zA-Z0-9_.]*$")
    operator: Literal["eq", "contains", "gt", "gte", "lt", "lte", "exists", "missing"] = "eq"
    value: str | float | bool | None = None

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
        if self.operator in {"gt", "gte", "lt", "lte"} and (
            not isinstance(self.value, (int, float)) or isinstance(self.value, bool)
        ):
            raise ValueError("Numeric comparisons require a number.")
        if self.operator == "contains" and not isinstance(self.value, str):
            raise ValueError("Contains comparisons require text.")
        return self


class Threshold(StrictModel):
    value: float = Field(default=70, ge=0, le=100)
    operator: Literal["gt", "gte", "lt", "lte"] = "gte"


class UpdateStatus(StrictModel):
    status: Literal["new", "qualified", "contacted", "won", "lost"] = "qualified"


class Delay(StrictModel):
    seconds: int = Field(default=60, ge=1, le=86400)


class Notification(StrictModel):
    message: str = Field(default="Workflow update", min_length=1, max_length=1000)


@dataclass(frozen=True)
class NodeSpec:
    type: str
    title: str
    config: builtins.type[StrictModel]
    category: Literal["trigger", "condition", "action"]
    side_effect: str = "none"
    timeout_seconds: int = 30
    retryable: bool = False
    roles: tuple[str, ...] = ("owner", "admin", "member")

    @property
    def outputs(self) -> tuple[str, ...]:
        return ("true", "false") if self.category == "condition" else ("default",)


SPECS = [
    NodeSpec("trigger.manual", "Manual trigger", Empty, "trigger"),
    NodeSpec("trigger.lead_created", "Lead created", Empty, "trigger"),
    NodeSpec("trigger.webhook", "Incoming webhook", Empty, "trigger"),
    NodeSpec("trigger.scheduled", "Scheduled trigger", Schedule, "trigger"),
    NodeSpec("condition.field", "Compare field", Condition, "condition"),
    NodeSpec("condition.score_threshold", "Score threshold", Threshold, "condition"),
    NodeSpec("action.validate_lead", "Validate lead", Empty, "action"),
    NodeSpec("action.detect_duplicate", "Check duplicate", Empty, "action"),
    NodeSpec("action.score_lead", "Score lead", Score, "action", "database"),
    NodeSpec(
        "action.generate_email_draft", "Generate outreach draft", Draft, "action", "ai", 60, True
    ),
    NodeSpec("action.request_approval", "Request approval", Approval, "action", "approval"),
    NodeSpec(
        "action.send_email",
        "Send approved email",
        Empty,
        "action",
        "external",
        30,
        False,
        ("owner", "admin"),
    ),
    NodeSpec("action.update_lead_status", "Update lead status", UpdateStatus, "action", "database"),
    NodeSpec(
        "action.internal_notification", "Internal notification", Notification, "action", "database"
    ),
    NodeSpec("action.delay", "Delay", Delay, "action", "schedule"),
    NodeSpec("action.record_result", "Record result", Empty, "action", "database"),
]
REGISTRY = {spec.type: spec for spec in SPECS}
