from dataclasses import dataclass, field
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.execution.errors import NodeFailure
from app.execution.logic import compare
from app.models import Lead, Notification, WorkflowExecution
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
    if node.type == "action.request_approval":
        payload = {"kind": config["kind"], "message": config["message"]}
        if config["kind"] == "email":
            draft = context.get("draft")
            if not isinstance(draft, dict):
                raise NodeFailure("DRAFT_REQUIRED", "Generate a validated draft before approval.")
            payload["draft"] = draft
        return Outcome({"approval_required": True}, approval=payload)
    raise NodeFailure(
        "NODE_NOT_CONFIGURED", "This node's provider or scoring service is not configured."
    )
