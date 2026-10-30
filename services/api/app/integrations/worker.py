import json
import time
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.base import now
from app.integrations.security import post_webhook, signature
from app.models import Integration, Membership, User, WebhookAttempt, WebhookDelivery
from app.schemas.integrations import WebhookConfig
from app.security.permissions import ADMIN_ROLES
from app.services.integrations import allowed_hosts

MAX_ATTEMPTS = 5


def retry_delay(number: int) -> int:
    return min(300, 5 * 2 ** max(0, number - 1))


def outcome(status: int | None, uncertain: bool, deduplicates: bool, number: int) -> str:
    if status is not None and 200 <= status < 300:
        return "delivered"
    if uncertain and not deduplicates:
        return "uncertain"
    if (
        deduplicates
        and number < MAX_ATTEMPTS
        and (uncertain or status == 429 or (status or 0) >= 500)
    ):
        return "retrying"
    return "failed"


async def deliver(factory: async_sessionmaker[AsyncSession], identifier: UUID) -> None:
    settings = get_settings()
    async with factory() as session:
        delivery = await session.scalar(
            select(WebhookDelivery).where(WebhookDelivery.id == identifier).with_for_update()
        )
        if (
            delivery is None
            or delivery.status not in {"queued", "retrying", "running"}
            or delivery.next_run_at > now()
        ):
            return
        if delivery.lease_until and delivery.lease_until > now():
            return
        item = await session.get(Integration, delivery.integration_id)
        assert item is not None
        config = WebhookConfig.model_validate(item.configuration)
        if delivery.status == "running":
            previous = await session.scalar(
                select(WebhookAttempt).where(
                    WebhookAttempt.delivery_id == identifier,
                    WebhookAttempt.number == delivery.attempt_count,
                )
            )
            if previous:
                previous.status, previous.uncertain, previous.error_code = (
                    "uncertain",
                    True,
                    "WORKER_LOST",
                )
                previous.completed_at = now()
            if not config.receiver_deduplicates or delivery.attempt_count >= MAX_ATTEMPTS:
                delivery.status, delivery.error_code = "uncertain", "WORKER_LOST"
                delivery.completed_at = now()
                await session.commit()
                return
        member = await session.scalar(
            select(Membership).where(
                Membership.organization_id == delivery.organization_id,
                Membership.user_id == delivery.requested_by,
            )
        )
        user = await session.get(User, delivery.requested_by)
        key = settings.webhook_signing_key.get_secret_value()
        if (
            not item.enabled
            or not config.destination
            or not key
            or not user
            or not user.is_active
            or not member
            or member.role not in ADMIN_ROLES
        ):
            delivery.status, delivery.error_code = "failed", "INTEGRATION_NOT_AUTHORIZED"
            delivery.completed_at = now()
            await session.commit()
            return
        delivery.attempt_count += 1
        delivery.status = "running"
        delivery.lease_token = token = uuid4()
        delivery.lease_until = now() + timedelta(seconds=45)
        attempt = WebhookAttempt(delivery_id=identifier, number=delivery.attempt_count)
        session.add(attempt)
        destination = config.destination
        deduplicates = config.receiver_deduplicates
        endpoint = str(item.id)
        body = json.dumps(delivery.payload, sort_keys=True, separators=(",", ":")).encode()
        number = delivery.attempt_count
        await session.commit()  # Intent is durable before touching the receiver.
    timestamp = int(time.time())
    status = None
    uncertain = False
    error = None
    try:
        status = await post_webhook(
            destination,
            allowed_hosts(),
            body,
            {
                "Content-Type": "application/json",
                "X-FlowOps-Event-ID": str(identifier),
                "Idempotency-Key": str(identifier),
                "X-FlowOps-Timestamp": str(timestamp),
                "X-FlowOps-Signature": signature(key, endpoint, timestamp, body),
            },
        )
        if not 200 <= status < 300:
            error = f"HTTP_{status}"
    except (ValueError, OSError, TimeoutError):
        error = "DESTINATION_BLOCKED"
    except httpx.HTTPError:
        uncertain, error = True, "DELIVERY_OUTCOME_UNKNOWN"
    async with factory() as session:
        delivery = await session.scalar(
            select(WebhookDelivery).where(WebhookDelivery.id == identifier).with_for_update()
        )
        if delivery is None or delivery.lease_token != token:
            return
        final_attempt = await session.scalar(
            select(WebhookAttempt).where(
                WebhookAttempt.delivery_id == identifier, WebhookAttempt.number == number
            )
        )
        assert final_attempt is not None
        delivery.status = outcome(status, uncertain, deduplicates, number)
        delivery.error_code = error
        delivery.lease_token, delivery.lease_until = None, None
        if delivery.status == "retrying":
            delivery.next_run_at = now() + timedelta(seconds=retry_delay(number))
        else:
            delivery.completed_at = now()
        final_attempt.status = delivery.status
        final_attempt.http_status, final_attempt.error_code, final_attempt.uncertain = (
            status,
            error,
            uncertain,
        )
        final_attempt.completed_at = now()
        await session.commit()


async def dispatch_webhooks(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as session:
        identifiers = list(
            await session.scalars(
                select(WebhookDelivery.id)
                .where(
                    WebhookDelivery.status.in_(["queued", "retrying", "running"]),
                    WebhookDelivery.next_run_at <= now(),
                    or_(
                        WebhookDelivery.lease_until.is_(None), WebhookDelivery.lease_until <= now()
                    ),
                )
                .order_by(WebhookDelivery.next_run_at)
                .limit(3)
            )
        )
    for identifier in identifiers:
        await deliver(factory, identifier)
