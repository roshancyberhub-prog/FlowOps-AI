import re
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.workflows.schema import StrictModel

Target = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


RequiredField = Literal["company", "job_title", "industry", "company_size", "website", "country"]


def default_required_fields() -> list[RequiredField]:
    return ["company", "job_title", "industry", "company_size"]


class ScoringConfig(StrictModel):
    schema_version: Literal[1] = 1
    target_titles: list[Target] = Field(
        default_factory=lambda: ["founder", "ceo", "cto", "head of", "director"], max_length=20
    )
    target_industries: list[Target] = Field(
        default_factory=lambda: ["software", "technology", "saas"], max_length=20
    )
    target_company_sizes: list[Target] = Field(
        default_factory=lambda: ["11-50", "51-200", "201-500"], max_length=20
    )
    personal_email_domains: list[Target] = Field(
        default_factory=lambda: [
            "gmail.com",
            "yahoo.com",
            "outlook.com",
            "hotmail.com",
            "icloud.com",
            "proton.me",
            "aol.com",
        ],
        max_length=100,
    )
    required_fields: list[RequiredField] = Field(
        default_factory=default_required_fields, max_length=6
    )
    title_weight: int = Field(default=25, strict=True, ge=0, le=100)
    industry_weight: int = Field(default=20, strict=True, ge=0, le=100)
    size_weight: int = Field(default=15, strict=True, ge=0, le=100)
    business_email_weight: int = Field(default=10, strict=True, ge=0, le=100)
    website_weight: int = Field(default=10, strict=True, ge=0, le=100)
    missing_penalty: int = Field(default=-10, strict=True, ge=-100, le=0)


@dataclass(frozen=True)
class ScoreResult:
    score: int
    reasons: list[dict]
    missing_fields: list[str]


def normalized(value: object) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def calculate_score(lead: dict, config: ScoringConfig) -> ScoreResult:
    title = normalized(lead.get("job_title"))
    title_fit = any(
        re.search(r"(?<!\w)" + re.escape(normalized(target)) + r"(?!\w)", title)
        for target in config.target_titles
        if normalized(target)
    )
    industry_fit = normalized(lead.get("industry")) in {
        normalized(t) for t in config.target_industries if normalized(t)
    }
    size_fit = normalized(lead.get("company_size")) in {
        normalized(t) for t in config.target_company_sizes if normalized(t)
    }
    email = normalized(lead.get("email"))
    domain = email.rsplit("@", 1)[-1] if "@" in email else ""
    business = bool(domain and domain not in {normalized(t) for t in config.personal_email_domains})
    website = bool(normalized(lead.get("website")))
    missing = sorted(
        {str(name) for name in config.required_fields if not normalized(lead.get(name))}
    )
    rules = [
        (
            "job_title",
            config.title_weight if title_fit else 0,
            "Job title matches a configured target phrase."
            if title_fit
            else "Job title does not match a target phrase.",
        ),
        (
            "industry",
            config.industry_weight if industry_fit else 0,
            "Industry matches the configured list."
            if industry_fit
            else "Industry is missing or outside the configured list.",
        ),
        (
            "company_size",
            config.size_weight if size_fit else 0,
            "Company size matches the configured list."
            if size_fit
            else "Company size is missing or outside the configured list.",
        ),
        (
            "business_email",
            config.business_email_weight if business else 0,
            "Email domain is outside the personal-domain list. "
            "This is a heuristic, not deliverability verification."
            if business
            else "Email domain is missing or on the personal-domain list.",
        ),
        (
            "website",
            config.website_weight if website else 0,
            "Website is present." if website else "Website is missing.",
        ),
        (
            "required_fields",
            config.missing_penalty if missing else 0,
            "Missing required fields: " + ", ".join(missing)
            if missing
            else "All configured required fields are present.",
        ),
    ]
    reasons = [{"rule": rule, "points": points, "reason": reason} for rule, points, reason in rules]
    return ScoreResult(max(0, min(100, sum(points for _, points, _ in rules))), reasons, missing)
