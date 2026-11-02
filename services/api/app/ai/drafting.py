from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import Completion, get_provider
from app.ai.schemas import DraftContent, Qualification
from app.core.config import get_settings
from app.execution.errors import NodeFailure
from app.models import EmailDraft, WorkflowExecution


def completion_metadata(result: Completion) -> dict:
    return {
        "provider": result.provider[:50],
        "model": result.model[:100],
        "prompt_version": result.prompt_version[:50],
        "usage": result.usage,
        "simulated": result.simulated,
    }


def draft_snapshot(draft: EmailDraft) -> dict:
    meta = draft.ai_metadata["draft"]
    return {
        "id": str(draft.id),
        "recipient": draft.recipient,
        "subject": draft.subject,
        "body": draft.body,
        "revision": draft.revision,
        "qualification": draft.qualification,
        "provided_facts": draft.provided_facts,
        "provider": meta["provider"],
        "model": meta["model"],
        "simulated": meta["simulated"],
    }


async def generate_draft(
    session: AsyncSession, run: WorkflowExecution, node_id: str, context: dict, config: dict
) -> EmailDraft:
    existing = await session.scalar(
        select(EmailDraft).where(
            EmailDraft.execution_id == run.id,
            EmailDraft.node_id == node_id,
            EmailDraft.organization_id == run.organization_id,
        )
    )
    if existing:
        return existing
    lead = context.get("lead")
    if not isinstance(lead, dict) or not lead.get("name") or not lead.get("email"):
        raise NodeFailure("LEAD_REQUIRED", "Choose a valid lead before generating a draft.")
    facts = {
        key: lead[key]
        for key in (
            "name",
            "company",
            "job_title",
            "industry",
            "company_size",
            "country",
            "website",
            "score",
        )
        if lead.get(key) is not None
    }
    settings = get_settings()
    provider = get_provider()
    if (
        settings.demo_retry_failure
        and settings.app_env != "production"
        and settings.ai_provider == "mock"
        and run.mode == "test"
        and run.node_attempt == 1
    ):
        raise NodeFailure(
            "DEMO_TRANSIENT_FAILURE",
            "Explicit demo fault: the mock provider is temporarily unavailable. Retrying safely.",
            transient=True,
        )
    try:
        qualified = await provider.qualify(facts)
        qualification = Qualification.model_validate(qualified.content)
        generated = await provider.draft(facts, config["value_proposition"], config["template"])
        content = DraftContent.model_validate(generated.content)
    except ValidationError as exc:
        raise NodeFailure(
            "AI_INVALID_OUTPUT",
            "The provider returned an invalid qualification or draft. No draft was saved.",
        ) from exc
    previous = context.get("draft", {}).get("id")
    if previous:
        old = await session.scalar(
            select(EmailDraft)
            .where(
                EmailDraft.id == UUID(previous),
                EmailDraft.execution_id == run.id,
                EmailDraft.organization_id == run.organization_id,
            )
            .with_for_update()
        )
        if old:
            old.status = "superseded"
    draft = EmailDraft(
        organization_id=run.organization_id,
        lead_id=UUID(context["lead_id"]) if context.get("lead_id") else None,
        execution_id=run.id,
        node_id=node_id,
        recipient=lead["email"],
        subject=content.subject,
        body=content.body,
        qualification=qualification.model_dump(mode="json"),
        provided_facts=facts,
        ai_metadata={
            "qualification": completion_metadata(qualified),
            "draft": completion_metadata(generated),
        },
    )
    session.add(draft)
    await session.flush()
    return draft
