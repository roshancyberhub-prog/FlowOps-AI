import hashlib
from dataclasses import dataclass
from typing import Protocol

from app.ai.schemas import DraftContent
from app.core.config import get_settings
from app.execution.errors import NodeFailure


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    message_id: str
    status: str
    simulated: bool


class EmailProvider(Protocol):
    async def send(
        self, recipient: str, content: DraftContent, idempotency_key: str
    ) -> DeliveryResult: ...


class MockEmailProvider:
    """Record a deterministic receipt; never connect to an email server."""

    async def send(
        self, recipient: str, content: DraftContent, idempotency_key: str
    ) -> DeliveryResult:
        identity = hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]
        return DeliveryResult("mock", f"mock-{identity}", "simulated", True)


def get_email_provider(mode: str) -> EmailProvider:
    if mode == "test" or get_settings().email_provider == "mock":
        return MockEmailProvider()
    raise NodeFailure(
        "EMAIL_NOT_CONFIGURED",
        "Email delivery is disabled. Configure mock email for the development demo.",
    )
