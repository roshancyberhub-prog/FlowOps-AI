from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from app.workflows.schema import StrictModel

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class Qualification(StrictModel):
    fit_category: Literal["qualified", "needs_review", "not_fit"]
    confidence: float = Field(ge=0, le=1, strict=True)
    reasoning_summary: str = Field(min_length=1, max_length=1000)
    missing_information: list[ShortText] = Field(max_length=12)
    recommended_next_step: str = Field(min_length=1, max_length=500)


class DraftContent(StrictModel):
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("subject")
    @classmethod
    def safe_subject(cls, value: str) -> str:
        if not value.strip() or any(
            ord(character) < 32 or ord(character) == 127 for character in value
        ):
            raise ValueError("Subject must be nonempty, single-line plain text.")
        return value.strip()

    @field_validator("body")
    @classmethod
    def safe_body(cls, value: str) -> str:
        if not value.strip() or "\0" in value:
            raise ValueError("Body must be nonempty text without null bytes.")
        return value.strip()
