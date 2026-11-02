from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.execution.errors import NodeFailure


@dataclass(frozen=True)
class Completion:
    content: dict
    provider: str
    model: str
    prompt_version: str
    usage: dict[str, int]
    simulated: bool


class AIProvider(Protocol):
    async def qualify(self, facts: dict) -> Completion: ...
    async def draft(self, facts: dict, value_proposition: str, template: str) -> Completion: ...


class MockAIProvider:
    """Explicit deterministic demo provider; makes no network calls."""

    async def qualify(self, facts: dict) -> Completion:
        score = facts.get("score", 0)
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            score = 0
        missing = [
            field
            for field in ("company", "job_title", "industry", "company_size")
            if not facts.get(field)
        ]
        return Completion(
            content={
                "fit_category": "qualified"
                if score >= 70
                else "not_fit"
                if score < 40
                else "needs_review",
                "confidence": 0.5,
                "reasoning_summary": (
                    "Mock qualification follows the recorded rule score. "
                    "It is a demonstration, not model judgment or a conversion prediction."
                ),
                "missing_information": missing,
                "recommended_next_step": "Review the provided lead facts before any outreach.",
            },
            provider="mock",
            model="deterministic-demo-v1",
            prompt_version="qualification-v1",
            usage={"input_tokens": 0, "output_tokens": 0},
            simulated=True,
        )

    async def draft(self, facts: dict, value_proposition: str, template: str) -> Completion:
        if template != "initial_follow_up":
            raise NodeFailure("UNKNOWN_TEMPLATE", "Choose a supported outreach template.")
        name = " ".join(str(facts.get("name") or "there").split())
        first_name = name.split()[0]
        company = " ".join(str(facts.get("company") or "your team").split())[:80]
        return Completion(
            content={
                "subject": f"A follow-up for {company}",
                "body": (
                    f"Hi {first_name},\n\n{value_proposition.strip()}\n\n"
                    f"Would a short conversation be useful for {company}?\n\nBest regards"
                ),
            },
            provider="mock",
            model="deterministic-demo-v1",
            prompt_version="outreach-v1",
            usage={"input_tokens": 0, "output_tokens": 0},
            simulated=True,
        )


def get_provider() -> AIProvider:
    if get_settings().ai_provider == "mock":
        return MockAIProvider()
    raise NodeFailure(
        "AI_NOT_CONFIGURED",
        "AI drafting is disabled. Configure the labelled mock provider for the development demo.",
    )
