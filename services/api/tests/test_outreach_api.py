from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.ai import drafting
from app.ai.providers import Completion
from app.core.config import get_settings
from app.db.session import session_factory
from app.execution.engine import process_execution
from app.main import app
from app.models import EmailDelivery, EmailDraft, Membership
from app.workflows.templates import make_graph
from tests.test_leads import account
from tests.test_scoring import FIT

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("isolate_rate_limit_keys", "mock_providers"),
]


@pytest.fixture
def mock_providers(monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_provider", "mock")
    monkeypatch.setattr(get_settings(), "email_provider", "mock")


async def setup_outreach(client, mode="test"):
    await account(client, f"outreach-{uuid4()}@example.com")
    org = (await client.post("/api/v1/organizations", json={"name": "Outreach team"})).json()
    headers = {"X-Organization-ID": org["id"]}
    lead = (await client.post("/api/v1/leads", headers=headers, json=FIT)).json()
    graph = make_graph(
        [
            "trigger.manual",
            "action.validate_lead",
            "action.detect_duplicate",
            "action.score_lead",
            "action.generate_email_draft",
            "action.request_approval",
            "action.send_email",
            "action.record_result",
        ]
    )
    workflow = (
        await client.post(
            "/api/v1/workflows",
            headers=headers,
            json={"name": "Reviewed mock outreach", "graph": graph.model_dump(by_alias=True)},
        )
    ).json()
    published = await client.post(
        "/api/v1/workflows/" + workflow["id"] + "/publish",
        headers=headers,
        json={"expected_revision": workflow["revision"]},
    )
    assert published.status_code == 200, published.text
    choices = await client.get("/api/v1/leads/" + lead["id"] + "/draft-workflows", headers=headers)
    assert choices.status_code == 200, choices.text
    assert choices.json()["items"][0]["workflow_id"] == workflow["id"]
    response = await client.post(
        "/api/v1/leads/" + lead["id"] + "/drafts",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={"workflow_id": workflow["id"], "mode": mode},
    )
    assert response.status_code == 202, response.text
    return headers, lead, response.json()


async def advance(client, headers, run_id):
    for _ in range(12):
        await process_execution(session_factory, UUID(run_id))
        run = (await client.get("/api/v1/executions/" + run_id, headers=headers)).json()
        if run["status"] in {"waiting_for_approval", "failed", "succeeded", "cancelled"}:
            return run
    raise AssertionError("Run did not reach a checkpoint")


def decision(approval):
    return {"revision": approval["revision"], "payload_hash": approval["payload_hash"]}


async def test_edit_invalidates_old_review_and_only_exact_approved_content_reaches_mock(
    monkeypatch,
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, lead, run = await setup_outreach(client)
        waiting = await advance(client, headers, run["id"])
        assert waiting["status"] == "waiting_for_approval", waiting
        drafts = (
            await client.get("/api/v1/leads/" + lead["id"] + "/drafts", headers=headers)
        ).json()["items"]
        assert len(drafts) == 1
        draft = drafts[0]
        assert draft["ai_metadata"]["draft"]["provider"] == "mock"
        assert draft["ai_metadata"]["draft"]["simulated"] is True
        assert "email" not in draft["provided_facts"]
        approval = (await client.get("/api/v1/approvals?status=pending", headers=headers)).json()[
            "items"
        ][0]
        patch = {
            "expected_revision": draft["revision"],
            "subject": "Human-reviewed subject",
            "body": "Human-reviewed fictional content.",
        }
        async with session_factory() as session:
            member = await session.scalar(
                select(Membership).where(
                    Membership.organization_id == UUID(headers["X-Organization-ID"])
                )
            )
            member.role = "viewer"
            await session.commit()
        assert (
            await client.patch("/api/v1/drafts/" + draft["id"], headers=headers, json=patch)
        ).status_code == 403
        async with session_factory() as session:
            member = await session.scalar(
                select(Membership).where(
                    Membership.organization_id == UUID(headers["X-Organization-ID"])
                )
            )
            member.role = "owner"
            await session.commit()
        edited = await client.patch("/api/v1/drafts/" + draft["id"], headers=headers, json=patch)
        assert edited.status_code == 200, edited.text
        assert edited.json()["revision"] == 2
        path = "/api/v1/approvals/" + approval["id"]
        assert (
            await client.post(path + "/approve", headers=headers, json=decision(approval))
        ).status_code == 409
        fresh = (await client.get(path, headers=headers)).json()
        assert fresh["revision"] == 2 and fresh["payload_hash"] != approval["payload_hash"]
        assert fresh["payload"]["draft"]["subject"] == patch["subject"]
        assert (
            await client.patch(
                "/api/v1/drafts/" + draft["id"],
                headers=headers,
                json={**patch, "expected_revision": 2, "recipient": "unreviewed@example.com"},
            )
        ).status_code == 422
        other = (
            await client.post("/api/v1/organizations", json={"name": "Other outreach team"})
        ).json()
        assert (
            await client.get(
                "/api/v1/drafts/" + draft["id"], headers={"X-Organization-ID": other["id"]}
            )
        ).status_code == 404
        approved = await client.post(path + "/approve", headers=headers, json=decision(fresh))
        assert approved.status_code == 200, approved.text
        assert (
            await client.patch(
                "/api/v1/drafts/" + draft["id"],
                headers=headers,
                json={**patch, "expected_revision": 2},
            )
        ).status_code == 409
        monkeypatch.setattr(get_settings(), "email_provider", "disabled")
        final = await advance(client, headers, run["id"])
        assert final["status"] == "succeeded", final
        await process_execution(session_factory, UUID(run["id"]))
        deliveries = (
            await client.get("/api/v1/deliveries?execution_id=" + run["id"], headers=headers)
        ).json()["items"]
        assert len(deliveries) == 1
        assert deliveries[0]["provider"] == "mock" and deliveries[0]["status"] == "simulated"
        assert deliveries[0]["delivery_metadata"] == {
            "simulated": True,
            "external_message_sent": False,
        }
        assert deliveries[0]["payload_hash"] == fresh["payload_hash"]
        assert (await client.get("/api/v1/drafts/" + draft["id"], headers=headers)).json()[
            "body"
        ] == patch["body"]
        async with session_factory() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(EmailDelivery)
                    .where(EmailDelivery.execution_id == UUID(run["id"]))
                )
                == 1
            )


async def test_invalid_provider_output_does_not_create_a_draft_or_approval(monkeypatch):
    class BadProvider:
        async def qualify(self, facts):
            return Completion(
                {"fit_category": "qualified", "confidence": 99},
                "mock",
                "invalid-output",
                "qualification-v1",
                {"input_tokens": 0, "output_tokens": 0},
                True,
            )

        async def draft(self, *args):
            raise AssertionError("Invalid qualification must stop drafting")

    monkeypatch.setattr(drafting, "get_provider", lambda: BadProvider())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, _, run = await setup_outreach(client)
        final = await advance(client, headers, run["id"])
        assert final["status"] == "failed" and final["error_code"] == "AI_INVALID_OUTPUT"
        async with session_factory() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(EmailDraft)
                    .where(EmailDraft.execution_id == UUID(run["id"]))
                )
                == 0
            )
        assert (await client.get("/api/v1/approvals", headers=headers)).json()["total"] == 0


async def test_disabled_ai_fails_explicitly_without_generating_content(monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_provider", "disabled")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, lead, run = await setup_outreach(client)
        final = await advance(client, headers, run["id"])
        assert final["status"] == "failed" and final["error_code"] == "AI_NOT_CONFIGURED"
        assert (
            await client.get("/api/v1/leads/" + lead["id"] + "/drafts", headers=headers)
        ).json()["total"] == 0


async def test_changed_live_recipient_blocks_delivery_after_approval():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, lead, run = await setup_outreach(client, mode="live")
        assert (await advance(client, headers, run["id"]))["status"] == "waiting_for_approval"
        approval = (await client.get("/api/v1/approvals?status=pending", headers=headers)).json()[
            "items"
        ][0]
        assert (
            await client.post(
                "/api/v1/approvals/" + approval["id"] + "/approve",
                headers=headers,
                json=decision(approval),
            )
        ).status_code == 200
        changed = await client.patch(
            "/api/v1/leads/" + lead["id"], headers=headers, json={"email": "changed@example.com"}
        )
        assert changed.status_code == 200
        final = await advance(client, headers, run["id"])
        assert final["status"] == "failed" and final["error_code"] == "RECIPIENT_CHANGED"
        assert (
            await client.get("/api/v1/deliveries?execution_id=" + run["id"], headers=headers)
        ).json()["total"] == 0


async def test_rejecting_email_checkpoint_cancels_without_a_delivery():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, _, run = await setup_outreach(client)
        assert (await advance(client, headers, run["id"]))["status"] == "waiting_for_approval"
        approval = (await client.get("/api/v1/approvals?status=pending", headers=headers)).json()[
            "items"
        ][0]
        rejected = await client.post(
            "/api/v1/approvals/" + approval["id"] + "/reject",
            headers=headers,
            json=decision(approval),
        )
        assert rejected.status_code == 200, rejected.text
        final = await advance(client, headers, run["id"])
        assert final["status"] == "cancelled"
        assert (
            await client.get("/api/v1/deliveries?execution_id=" + run["id"], headers=headers)
        ).json()["total"] == 0
