from dataclasses import dataclass, field
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.drafting import draft_snapshot, generate_draft
from app.db.base import now
from app.email.delivery import deliver_approved_email
from app.execution.errors import NodeFailure
from app.execution.logic import compare
from app.leads.scoring import ScoringConfig, calculate_score
from app.models import EmailDraft, Lead, Notification, ScoringProfile, WorkflowExecution
from app.schemas.leads import LeadCreate
from app.workflows.registry import REGISTRY
from app.workflows.schema import Node


@dataclass
class Outcome:
    output: dict = field(default_factory=dict)
    handle: str = "default"
    delay_seconds: int = 0
    approval: dict | None = None


async def handle_node(
    session: AsyncSession, run: WorkflowExecution, node: Node, context: dict
) -> Outcome:
    config = REGISTRY[node.type].config.model_validate(node.config).model_dump()
    if node.type.startswith("trigger."):
        return Outcome({"trigger": run.trigger_type})
    if node.type.startswith("condition."):
        field_name = config.get("field", "lead.score")
        matched = compare(context, field_name, config["operator"], config.get("value"))
        return Outcome({"matched": matched}, "true" if matched else "false")
    if node.type == "action.validate_lead":
        lead_data = context.get("lead", {})
        fields = {key: value for key, value in lead_data.items() if key in LeadCreate.model_fields}
        try:
            LeadCreate.model_validate(fields)
        except ValidationError as exc:
            raise NodeFailure(
                "INVALID_LEAD", "The run requires a valid lead name and email."
            ) from exc
        return Outcome({"valid": True})
    if node.type == "action.detect_duplicate":
        email = context.get("lead", {}).get("email")
        if not email:
            raise NodeFailure("LEAD_REQUIRED", "Choose a lead before checking duplicates.")
        query = select(Lead.id).where(
            Lead.organization_id == run.organization_id, Lead.email == email
        )
        if context.get("lead_id"):
            query = query.where(Lead.id != UUID(context["lead_id"]))
        duplicate = await session.scalar(query.limit(1)) is not None
        context["duplicate"] = duplicate
        return Outcome({"duplicate": duplicate})
    if node.type == "action.score_lead":
        if not context.get("lead"):
            raise NodeFailure("LEAD_REQUIRED", "Choose a lead before scoring.")
        profile_query = select(ScoringProfile).where(
            ScoringProfile.organization_id == run.organization_id
        )
        configured = config["scoring_profile"]
        # Definitions published before scoring existed retain the immutable baseline.
        profile_query = (
            profile_query.where(ScoringProfile.version_number == 1)
            if configured == "default"
            else profile_query.where(ScoringProfile.id == UUID(configured))
        )
        profile = await session.scalar(profile_query)
        if profile is None:
            raise NodeFailure(
                "PROFILE_UNAVAILABLE", "This workflow's scoring profile is unavailable."
            )
        result = calculate_score(
            context["lead"], ScoringConfig.model_validate(profile.configuration)
        )
        scored_at = now()
        context["lead"].update(
            {
                "score": result.score,
                "score_reasons": result.reasons,
                "score_profile_id": str(profile.id),
                "score_profile_version": profile.version_number,
                "scored_at": scored_at.isoformat(),
            }
        )
        if run.mode == "live":
            if not context.get("lead_id"):
                raise NodeFailure("STORED_LEAD_REQUIRED", "Live scoring requires a stored lead.")
            lead = await session.scalar(
                select(Lead)
                .where(
                    Lead.id == UUID(context["lead_id"]), Lead.organization_id == run.organization_id
                )
                .with_for_update()
            )
            if lead is None or lead.status == "archived":
                raise NodeFailure("LEAD_UNAVAILABLE", "The lead is unavailable or archived.")
            if any(
                getattr(lead, field) != context["lead"].get(field)
                for field in (
                    "email",
                    "company",
                    "job_title",
                    "industry",
                    "company_size",
                    "website",
                    "country",
                )
            ):
                raise NodeFailure(
                    "LEAD_CHANGED", "The lead changed after this run started. Start a new run."
                )
            lead.score = result.score
            lead.score_reasons = result.reasons
            lead.score_profile_id = profile.id
            lead.score_profile_version = profile.version_number
            lead.scored_at = scored_at
        return Outcome(
            {
                "score": result.score,
                "reasons": result.reasons,
                "profile_id": str(profile.id),
                "profile_version": profile.version_number,
                "missing_fields": result.missing_fields,
                "simulated": run.mode == "test",
            }
        )
    if node.type == "action.update_lead_status":
        if "lead" not in context:
            raise NodeFailure("LEAD_REQUIRED", "Choose a lead before changing its status.")
        if run.mode == "live":
            if not context.get("lead_id"):
                raise NodeFailure("STORED_LEAD_REQUIRED", "Live changes require a stored lead.")
            lead = await session.scalar(
                select(Lead)
                .where(
                    Lead.id == UUID(context["lead_id"]), Lead.organization_id == run.organization_id
                )
                .with_for_update()
            )
            if lead is None or lead.status == "archived":
                raise NodeFailure("LEAD_UNAVAILABLE", "The lead is unavailable or archived.")
            lead.status = config["status"]
        context["lead"]["status"] = config["status"]
        return Outcome({"status": config["status"], "simulated": run.mode == "test"})
    if node.type == "action.internal_notification":
        if run.mode == "live":
            session.add(
                Notification(
                    organization_id=run.organization_id,
                    execution_id=run.id,
                    node_id=node.id,
                    message=config["message"],
                )
            )
        return Outcome({"message": config["message"], "simulated": run.mode == "test"})
    if node.type == "action.delay":
        return Outcome(
            {"scheduled_delay_seconds": config["seconds"]}, delay_seconds=config["seconds"]
        )
    if node.type == "action.record_result":
        return Outcome({"recorded": True, "mode": run.mode})
    if node.type == "action.generate_email_draft":
        draft = await generate_draft(session, run, node.id, context, config)
        context["draft"] = draft_snapshot(draft)
        context.pop("approval", None)
        context.pop("email_approval", None)
        return Outcome(
            {
                "draft_id": str(draft.id),
                "provider": draft.ai_metadata["draft"]["provider"],
                "simulated": draft.ai_metadata["draft"]["simulated"],
                "revision": draft.revision,
            }
        )
    if node.type == "action.send_email":
        delivery = await deliver_approved_email(session, run, node.id, context)
        context["delivery"] = {
            "id": str(delivery.id),
            "provider": delivery.provider,
            "status": delivery.status,
            **delivery.delivery_metadata,
        }
        return Outcome(context["delivery"])
    if node.type == "action.request_approval":
        payload = {"kind": config["kind"], "message": config["message"]}
        payload["mode"] = run.mode
        if config["kind"] == "email":
            saved_id = context.get("draft", {}).get("id")
            if not saved_id:
                raise NodeFailure("DRAFT_REQUIRED", "Generate a validated draft before approval.")
            draft_record = await session.scalar(
                select(EmailDraft)
                .where(
                    EmailDraft.id == UUID(saved_id),
                    EmailDraft.execution_id == run.id,
                    EmailDraft.organization_id == run.organization_id,
                )
                .with_for_update()
            )
            if draft_record is None or draft_record.status != "pending_review":
                raise NodeFailure("DRAFT_UNAVAILABLE", "The current draft is not awaiting review.")
            payload["draft"] = draft_snapshot(draft_record)
            context["draft"] = payload["draft"]
        return Outcome({"approval_required": True}, approval=payload)
    raise NodeFailure(
        "NODE_NOT_CONFIGURED", "This node's provider or scoring service is not configured."
    )
