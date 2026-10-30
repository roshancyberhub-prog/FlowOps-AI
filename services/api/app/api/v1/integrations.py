from datetime import timedelta
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import now
from app.db.session import get_session
from app.execution.hashing import payload_hash
from app.integrations.github import IntegrationError, repository
from app.models import (
    Integration,
    Membership,
    Organization,
    WebhookAttempt,
    WebhookDelivery,
    WebhookEvent,
    WorkflowExecution,
)
from app.schemas.integrations import (
    DeliveryCreate,
    GitHubConfig,
    IntegrationCreate,
    IntegrationPatch,
    IntegrationRead,
    WebhookConfig,
)
from app.security.permissions import ADMIN_ROLES, membership, require_role
from app.services.integrations import configuration, get_integration, receive
from app.services.leads import audit

router = APIRouter(tags=["integrations"])


@router.get("/integrations")
async def listing(
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1, le=10000),
) -> dict:
    query = select(Integration).where(Integration.organization_id == member.organization_id)
    rows = await session.scalars(
        query.order_by(Integration.created_at.desc()).offset((page - 1) * 25).limit(25)
    )
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    return {
        "items": [IntegrationRead.model_validate(x) for x in rows],
        "total": total or 0,
        "page": page,
    }


@router.post("/integrations", response_model=IntegrationRead, status_code=201)
async def create(
    data: IntegrationCreate,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Integration:
    require_role(member, ADMIN_ROLES)
    config = await configuration(session, member.organization_id, data.provider, data.configuration)
    await session.scalar(
        select(Organization).where(Organization.id == member.organization_id).with_for_update()
    )
    count = await session.scalar(
        select(func.count())
        .select_from(Integration)
        .where(Integration.organization_id == member.organization_id)
    )
    if (count or 0) >= 100:
        raise HTTPException(409, "This workspace has reached the limit of 100 integrations.")
    item = Integration(
        organization_id=member.organization_id,
        created_by=member.user_id,
        name=data.name,
        provider=data.provider,
        configuration=config,
    )
    session.add(item)
    await session.flush()
    audit(session, member, "integration.created", item.id, request.state.request_id)
    await session.commit()
    return item


@router.patch("/integrations/{identifier}", response_model=IntegrationRead)
async def update(
    identifier: UUID,
    data: IntegrationPatch,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Integration:
    require_role(member, ADMIN_ROLES)
    item = await get_integration(session, member.organization_id, identifier)
    await session.refresh(item, with_for_update=True)
    if item.revision != data.expected_revision:
        raise HTTPException(409, "This integration changed. Refresh and try again.")
    item.enabled = data.enabled
    item.revision += 1
    audit(session, member, "integration.updated", item.id, request.state.request_id)
    await session.commit()
    return item


@router.post("/integrations/{identifier}/test", response_model=IntegrationRead)
async def test(
    identifier: UUID,
    request: Request,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> Integration:
    require_role(member, ADMIN_ROLES)
    item = await get_integration(session, member.organization_id, identifier)
    await session.refresh(item, with_for_update=True)
    if not item.enabled:
        raise HTTPException(409, "Enable this integration before testing it.")
    if item.last_test_at and item.last_test_at > now() - timedelta(seconds=30):
        raise HTTPException(429, "Wait 30 seconds between connection tests.")
    item.last_test_at = now()
    item.last_result = {}
    item.last_error = None
    try:
        if item.provider == "github":
            config = GitHubConfig.model_validate(item.configuration)
            item.last_result = await repository(config.owner, config.repo)
        elif not get_settings().webhook_signing_key.get_secret_value():
            raise IntegrationError("SIGNING_KEY_MISSING")
        item.last_test_status = "connected"
    except (IntegrationError, httpx.HTTPError, ValidationError) as exc:
        item.last_test_status = "failed"
        item.last_error = exc.code if isinstance(exc, IntegrationError) else "PROVIDER_UNAVAILABLE"
    audit(session, member, "integration.tested", item.id, request.state.request_id)
    await session.commit()
    return item


@router.get("/integrations/{identifier}/events")
async def events(
    identifier: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await get_integration(session, member.organization_id, identifier)
    rows = await session.scalars(
        select(WebhookEvent)
        .where(WebhookEvent.integration_id == identifier)
        .order_by(WebhookEvent.created_at.desc())
        .limit(50)
    )
    return {
        "items": [
            {
                "id": x.id,
                "external_id": x.external_id,
                "lead_id": x.lead_id,
                "execution_id": x.execution_id,
                "created_at": x.created_at,
            }
            for x in rows
        ]
    }


@router.post("/webhooks/{identifier}")
async def incoming(
    identifier: UUID, request: Request, session: AsyncSession = Depends(get_session)
) -> dict:
    return await receive(
        session,
        identifier,
        await request.body(),
        request.headers.get("X-FlowOps-Timestamp", ""),
        request.headers.get("X-FlowOps-Signature", ""),
        request.state.request_id,
    )


@router.post("/integrations/{identifier}/deliveries", status_code=202)
async def send(
    identifier: UUID,
    data: DeliveryCreate,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=200),
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> dict:
    require_role(member, ADMIN_ROLES)
    item = await get_integration(session, member.organization_id, identifier)
    if (
        item.provider != "webhook"
        or not item.enabled
        or not WebhookConfig.model_validate(item.configuration).destination
    ):
        raise HTTPException(409, "Enable a webhook integration with an outgoing destination.")
    if not get_settings().webhook_signing_key.get_secret_value():
        raise HTTPException(503, "Webhook signing is not configured.")
    await session.scalar(
        select(Organization).where(Organization.id == member.organization_id).with_for_update()
    )
    digest = payload_hash(data.model_dump(mode="json"))
    existing = await session.scalar(
        select(WebhookDelivery).where(
            WebhookDelivery.integration_id == identifier,
            WebhookDelivery.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.input_hash != digest:
            raise HTTPException(409, "Idempotency key was already used for different input.")
        return {"id": existing.id, "status": existing.status}
    pending = await session.scalar(
        select(func.count())
        .select_from(WebhookDelivery)
        .where(
            WebhookDelivery.organization_id == member.organization_id,
            WebhookDelivery.status.in_(["queued", "retrying", "running"]),
        )
    )
    if (pending or 0) >= 100:
        raise HTTPException(409, "Wait for existing webhook deliveries to finish.")
    envelope: dict = {"type": "integration.test", "organization_id": str(member.organization_id)}
    if data.execution_id:
        run = await session.scalar(
            select(WorkflowExecution).where(
                WorkflowExecution.id == data.execution_id,
                WorkflowExecution.organization_id == member.organization_id,
            )
        )
        if run is None:
            raise HTTPException(404, "Execution not found.")
        envelope = {
            **envelope,
            "type": "execution.status",
            "execution_id": str(run.id),
            "status": run.status,
        }
    identifier = uuid4()
    delivery = WebhookDelivery(
        id=identifier,
        organization_id=member.organization_id,
        integration_id=item.id,
        requested_by=member.user_id,
        idempotency_key=idempotency_key,
        input_hash=digest,
        payload={**envelope, "event_id": str(identifier)},
    )
    session.add(delivery)
    audit(session, member, "webhook.queued", identifier, request.state.request_id)
    await session.commit()
    return {"id": delivery.id, "status": delivery.status}


@router.get("/integrations/{identifier}/deliveries")
async def deliveries(
    identifier: UUID,
    member: Membership = Depends(membership),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await get_integration(session, member.organization_id, identifier)
    rows = await session.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.integration_id == identifier)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(50)
    )
    result = []
    for row in rows:
        attempts = await session.scalars(
            select(WebhookAttempt)
            .where(WebhookAttempt.delivery_id == row.id)
            .order_by(WebhookAttempt.number)
        )
        result.append(
            {
                "id": row.id,
                "status": row.status,
                "error_code": row.error_code,
                "created_at": row.created_at,
                "attempts": [
                    {
                        "number": x.number,
                        "status": x.status,
                        "http_status": x.http_status,
                        "error_code": x.error_code,
                        "uncertain": x.uncertain,
                    }
                    for x in attempts
                ],
            }
        )
    return {"items": result}
