import hashlib
import time
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.execution.triggers import create_automatic_run, lead_created
from app.integrations.security import validate_destination, verify_signature
from app.models import Integration, Lead, Organization, WebhookEvent, Workflow, WorkflowVersion
from app.schemas.integrations import GitHubConfig, IncomingEvent, WebhookConfig
from app.schemas.leads import LeadRead
from app.workflows.schema import Graph


async def get_integration(session: AsyncSession, org: UUID, identifier: UUID) -> Integration:
    item = await session.scalar(
        select(Integration).where(Integration.id == identifier, Integration.organization_id == org)
    )
    if item is None:
        raise HTTPException(404, "Integration not found.")
    return item


async def configuration(session: AsyncSession, org: UUID, provider: str, data: dict) -> dict:
    try:
        if provider == "github":
            return GitHubConfig.model_validate(data).model_dump()
        config = WebhookConfig.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(422, "Check the integration settings.") from exc
    if config.workflow_id:
        workflow = await session.scalar(
            select(Workflow).where(
                Workflow.id == config.workflow_id, Workflow.organization_id == org
            )
        )
        if not workflow:
            raise HTTPException(404, "Workflow not found.")
    if config.destination:
        try:
            await validate_destination(config.destination, allowed_hosts())
        except (ValueError, OSError, TimeoutError) as exc:
            raise HTTPException(
                422, "Destination is not an allowlisted public HTTPS endpoint."
            ) from exc
    return config.model_dump(mode="json")


def allowed_hosts() -> set[str]:
    return {
        host.strip().lower()
        for host in get_settings().webhook_allowed_hosts.split(",")
        if host.strip()
    }


async def receive(
    session: AsyncSession,
    identifier: UUID,
    body: bytes,
    timestamp: str,
    signed: str,
    correlation: str,
) -> dict:
    if len(body) > 65536:
        raise HTTPException(413, "Webhook events are limited to 64 KiB.")
    key = get_settings().webhook_signing_key.get_secret_value()
    if not key:
        raise HTTPException(503, "Webhook signing is not configured.")
    if not verify_signature(key, str(identifier), timestamp, signed, body, int(time.time())):
        raise HTTPException(401, "Invalid or expired webhook signature.")
    try:
        data = IncomingEvent.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, "Use an event_id and a valid lead object.") from exc
    item = await session.get(Integration, identifier)
    if not item or item.provider != "webhook" or not item.enabled:
        raise HTTPException(404, "Webhook not available.")
    # Serializes inbound retries and lead creation for this workspace.
    await session.scalar(
        select(Organization).where(Organization.id == item.organization_id).with_for_update()
    )
    digest = hashlib.sha256(body).hexdigest()
    existing = await session.scalar(
        select(WebhookEvent).where(
            WebhookEvent.integration_id == identifier, WebhookEvent.external_id == data.event_id
        )
    )
    if existing:
        if existing.body_hash != digest:
            raise HTTPException(409, "Event ID was already used with a different body.")
        return event_result(existing, True)
    lead = await session.scalar(
        select(Lead).where(
            Lead.organization_id == item.organization_id, Lead.email == str(data.lead.email)
        )
    )
    if lead is None:
        lead = Lead(organization_id=item.organization_id, **data.lead.model_dump(mode="json"))
        session.add(lead)
        await session.flush()
        await lead_created(session, lead, correlation)
    elif lead.status == "archived":
        raise HTTPException(409, "This lead is archived; restore it before triggering a workflow.")
    event = WebhookEvent(
        organization_id=item.organization_id,
        integration_id=item.id,
        external_id=data.event_id,
        body_hash=digest,
        lead_id=lead.id,
    )
    session.add(event)
    await session.flush()
    config = WebhookConfig.model_validate(item.configuration)
    if config.workflow_id:
        workflow = await session.scalar(
            select(Workflow).where(
                Workflow.id == config.workflow_id,
                Workflow.organization_id == item.organization_id,
                Workflow.status == "active",
            )
        )
        version = (
            await session.get(WorkflowVersion, workflow.current_version_id) if workflow else None
        )
        if (
            workflow is None
            or version is None
            or not any(
                n.type == "trigger.webhook"
                for n in Graph.model_validate(version.graph_definition).nodes
            )
        ):
            raise HTTPException(409, "Publish and activate a workflow with a webhook trigger.")
        run = await create_automatic_run(
            session,
            workflow,
            version,
            "trigger.webhook",
            f"webhook:{event.id}",
            {
                "lead_id": str(lead.id),
                "lead": LeadRead.model_validate(lead).model_dump(mode="json"),
                "webhook_event_id": str(event.id),
            },
            correlation,
        )
        event.execution_id = run.id
    await session.commit()
    return event_result(event, False)


def event_result(event: WebhookEvent, duplicate: bool) -> dict:
    return {
        "id": str(event.id),
        "lead_id": str(event.lead_id),
        "execution_id": str(event.execution_id) if event.execution_id else None,
        "duplicate": duplicate,
    }
