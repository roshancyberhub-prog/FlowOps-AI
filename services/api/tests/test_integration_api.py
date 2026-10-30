import json
import time
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import get_settings
from app.db.base import now
from app.db.session import session_factory
from app.integrations import worker
from app.integrations.security import signature
from app.main import app
from app.models import Membership, WebhookDelivery
from app.workflows.templates import make_graph
from tests.test_leads import account
from tests.test_scoring import FIT

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("isolate_rate_limit_keys")]


@pytest.fixture(autouse=True)
def signing(monkeypatch):
    monkeypatch.setattr(get_settings(), "webhook_signing_key", SecretStr("test-only-key"))


async def setup(client, config=None):
    await account(client, f"integration-{uuid4()}@example.com")
    org = (
        await client.post("/api/v1/organizations", json={"name": "Integration workspace"})
    ).json()
    headers = {"X-Organization-ID": org["id"]}
    response = await client.post(
        "/api/v1/integrations",
        headers=headers,
        json={"name": "Signed lead events", "provider": "webhook", "configuration": config or {}},
    )
    assert response.status_code == 201, response.text
    return headers, response.json()


def signed_headers(identifier, body, timestamp=None):
    timestamp = timestamp or int(time.time())
    return {
        "X-FlowOps-Timestamp": str(timestamp),
        "X-FlowOps-Signature": signature("test-only-key", identifier, timestamp, body),
        "Content-Type": "application/json",
    }


async def test_signed_ingress_deduplicates_and_persists_automatic_run_without_overwrite():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, item = await setup(client)
        graph = make_graph(["trigger.webhook", "action.validate_lead", "action.record_result"])
        workflow = (
            await client.post(
                "/api/v1/workflows",
                headers=headers,
                json={"name": "Inbound", "graph": graph.model_dump(by_alias=True)},
            )
        ).json()
        published = await client.post(
            "/api/v1/workflows/" + workflow["id"] + "/publish",
            headers=headers,
            json={"expected_revision": workflow["revision"]},
        )
        assert published.status_code == 200, published.text
        item = (
            await client.post(
                "/api/v1/integrations",
                headers=headers,
                json={
                    "name": "Workflow event",
                    "provider": "webhook",
                    "configuration": {"workflow_id": workflow["id"]},
                },
            )
        ).json()
        path = "/api/v1/webhooks/" + item["id"]
        body = json.dumps({"event_id": "lead:001", "lead": FIT}).encode()
        response = await client.post(path, content=body, headers=signed_headers(item["id"], body))
        assert response.status_code == 200, response.text
        assert response.json()["execution_id"] and not response.json()["duplicate"]
        duplicate = await client.post(path, content=body, headers=signed_headers(item["id"], body))
        assert duplicate.json()["id"] == response.json()["id"] and duplicate.json()["duplicate"]
        otherbody = json.dumps(
            {"event_id": "lead:001", "lead": {**FIT, "name": "Changed"}}
        ).encode()
        assert (
            await client.post(
                path, content=otherbody, headers=signed_headers(item["id"], otherbody)
            )
        ).status_code == 409
        assert (
            await client.post(path, content=body, headers=signed_headers(str(uuid4()), body))
        ).status_code == 401
        assert (
            await client.post(
                path, content=body, headers=signed_headers(item["id"], body, int(time.time()) - 301)
            )
        ).status_code == 401
        assert (
            await client.get("/api/v1/integrations/" + item["id"] + "/events", headers=headers)
        ).json()["items"][0]["external_id"] == "lead:001"
        other = (await client.post("/api/v1/organizations", json={"name": "Other tenant"})).json()
        assert (
            await client.get(
                "/api/v1/integrations/" + item["id"] + "/events",
                headers={"X-Organization-ID": other["id"]},
            )
        ).status_code == 404
        async with session_factory() as session:
            member = await session.scalar(
                select(Membership).where(
                    Membership.organization_id == UUID(headers["X-Organization-ID"])
                )
            )
            member.role = "viewer"
            await session.commit()
        denied = await client.post("/api/v1/integrations/" + item["id"] + "/test", headers=headers)
        assert denied.status_code == 403


async def test_connection_success_and_failure_are_visible(monkeypatch):
    async def ok(owner, repo):
        return {"full_name": "octocat/Hello-World", "url": "https://github.com/octocat/Hello-World"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, _ = await setup(client)
        created = await client.post(
            "/api/v1/integrations",
            headers=headers,
            json={
                "name": "Public repo",
                "provider": "github",
                "configuration": {"owner": "octocat", "repo": "Hello-World"},
            },
        )
        item = created.json()
        monkeypatch.setattr("app.api.v1.integrations.repository", ok)
        response = await client.post(
            "/api/v1/integrations/" + item["id"] + "/test", headers=headers
        )
        assert response.json()["last_test_status"] == "connected"
        assert "key" not in response.text

        async def fails(owner, repo):
            raise httpx.ConnectError("must not leak provider details")

        monkeypatch.setattr("app.api.v1.integrations.repository", fails)
        another = (
            await client.post(
                "/api/v1/integrations",
                headers=headers,
                json={
                    "name": "Unavailable repo",
                    "provider": "github",
                    "configuration": {"owner": "octocat", "repo": "Hello-World"},
                },
            )
        ).json()
        response = await client.post(
            "/api/v1/integrations/" + another["id"] + "/test", headers=headers
        )
        assert response.json()["last_test_status"] == "failed"
        assert response.json()["last_error"] == "PROVIDER_UNAVAILABLE"
        assert "must not leak" not in response.text


@pytest.mark.parametrize("deduplicates", [True, False])
async def test_outgoing_uncertainty_requires_receiver_contract(monkeypatch, deduplicates):
    async def validate(url, allowed):
        return httpx.URL(url), "8.8.8.8"

    monkeypatch.setattr("app.services.integrations.validate_destination", validate)
    attempts = []

    async def send(url, allowed, body, headers):
        attempts.append(headers["Idempotency-Key"])
        assert b"@" not in body  # Operational envelopes do not export lead contact data.
        if len(attempts) == 1:
            raise httpx.ReadTimeout("unknown receiver outcome")
        return 204

    monkeypatch.setattr(worker, "post_webhook", send)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, item = await setup(
            client,
            {
                "destination": "https://receiver.example/events",
                "receiver_deduplicates": deduplicates,
            },
        )
        path = "/api/v1/integrations/" + item["id"]
        response = await client.post(
            path + "/deliveries",
            headers={**headers, "Idempotency-Key": "durable-test-event"},
            json={},
        )
        assert response.status_code == 202, response.text
        identifier = UUID(response.json()["id"])
        duplicate = await client.post(
            path + "/deliveries",
            headers={**headers, "Idempotency-Key": "durable-test-event"},
            json={},
        )
        assert duplicate.json()["id"] == str(identifier)
        await worker.deliver(session_factory, identifier)
        async with session_factory() as session:
            delivery = await session.get(WebhookDelivery, identifier)
            assert delivery.status == ("retrying" if deduplicates else "uncertain")
            delivery.next_run_at = now() - timedelta(seconds=1)
            await session.commit()
        await worker.deliver(session_factory, identifier)
        rows = (await client.get(path + "/deliveries", headers=headers)).json()["items"]
        assert rows[0]["status"] == ("delivered" if deduplicates else "uncertain")
        assert len(rows[0]["attempts"]) == (2 if deduplicates else 1)
        assert len(set(attempts)) == 1
