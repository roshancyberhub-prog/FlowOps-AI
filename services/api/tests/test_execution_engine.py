from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.base import now
from app.db.session import session_factory
from app.execution import engine
from app.execution.errors import NodeFailure
from app.main import app
from app.models import ExecutionStep, Membership, WorkflowExecution
from app.workflows.templates import make_graph
from tests.test_leads import account

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("isolate_rate_limit_keys")]


async def prepare(client, types, configs=None):
    await account(client, f"engine-{uuid4()}@example.com")
    org = (await client.post("/api/v1/organizations", json={"name": "Engine team"})).json()
    headers = {"X-Organization-ID": org["id"]}
    graph = make_graph(types)
    for index, config in (configs or {}).items():
        graph.nodes[index].config = config
    created = (
        await client.post("/api/v1/workflows", headers=headers, json={"name": "Background process"})
    ).json()
    path = f"/api/v1/workflows/{created['id']}"
    saved = await client.patch(
        path,
        headers=headers,
        json={"expected_revision": created["revision"], "graph": graph.model_dump(by_alias=True)},
    )
    assert saved.status_code == 200, saved.text
    published = await client.post(
        path + "/publish", headers=headers, json={"expected_revision": saved.json()["revision"]}
    )
    assert published.status_code == 200, published.text
    response = await client.post(
        path + "/test-runs", headers={**headers, "Idempotency-Key": str(uuid4())}, json={}
    )
    assert response.status_code == 202, response.text
    return headers, response.json()


async def test_steps_are_persisted_and_duplicate_delivery_is_harmless():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, run = await prepare(client, ["trigger.manual", "action.record_result"])
        run_id = UUID(run["id"])
        await engine.process_execution(session_factory, run_id)
        await engine.process_execution(session_factory, run_id)
        await engine.process_execution(session_factory, run_id)
        result = await client.get("/api/v1/executions/" + run["id"], headers=headers)
        assert result.json()["status"] == "succeeded"
        steps = (
            await client.get("/api/v1/executions/" + run["id"] + "/steps", headers=headers)
        ).json()
        assert steps["total"] == 2
        assert all(step["status"] == "succeeded" for step in steps["items"])


async def test_transient_failure_retries_then_dead_letters_with_history(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, run = await prepare(client, ["trigger.manual", "action.record_result"])
        run_id = UUID(run["id"])
        await engine.process_execution(session_factory, run_id)

        async def unavailable(*args):
            raise NodeFailure(
                "TEMPORARY_UNAVAILABLE", "The service is temporarily unavailable.", transient=True
            )

        monkeypatch.setattr(engine, "handle_node", unavailable)
        for attempt in range(3):
            await engine.process_execution(session_factory, run_id)
            async with session_factory() as session:
                saved = await session.get(WorkflowExecution, run_id)
                assert saved.status == ("failed" if attempt == 2 else "retrying")
                saved.next_run_at = now() - timedelta(seconds=1)
                await session.commit()
        result = (await client.get("/api/v1/executions/" + run["id"], headers=headers)).json()
        assert result["dead_letter"] and result["node_attempt"] == 3
        steps = (
            await client.get("/api/v1/executions/" + run["id"] + "/steps", headers=headers)
        ).json()["items"]
        assert len(steps) == 4
        assert [s["attempt_number"] for s in steps if s["node_id"] == "node_1"] == [1, 2, 3]
        assert (
            await client.post("/api/v1/executions/" + run["id"] + "/retry", headers=headers)
        ).status_code == 200


async def test_approval_requires_current_review_and_admin_then_resumes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, run = await prepare(
            client,
            ["trigger.manual", "action.request_approval", "action.record_result"],
            {1: {"kind": "continue"}},
        )
        run_id = UUID(run["id"])
        await engine.process_execution(session_factory, run_id)
        await engine.process_execution(session_factory, run_id)
        approvals = (await client.get("/api/v1/approvals", headers=headers)).json()["items"]
        assert len(approvals) == 1
        approval = approvals[0]
        path = "/api/v1/approvals/" + approval["id"] + "/approve"
        data = {"revision": approval["revision"], "payload_hash": approval["payload_hash"]}
        assert (
            await client.post(path, headers=headers, json={**data, "revision": 99})
        ).status_code == 409
        async with session_factory() as session:
            member = await session.scalar(
                select(Membership).where(
                    Membership.organization_id == UUID(headers["X-Organization-ID"])
                )
            )
            member.role = "viewer"
            await session.commit()
        assert (await client.post(path, headers=headers, json=data)).status_code == 403
        async with session_factory() as session:
            member = await session.scalar(
                select(Membership).where(
                    Membership.organization_id == UUID(headers["X-Organization-ID"])
                )
            )
            member.role = "owner"
            await session.commit()
        assert (await client.post(path, headers=headers, json=data)).status_code == 200
        assert (await client.post(path, headers=headers, json=data)).status_code == 409
        await engine.process_execution(session_factory, run_id)
        assert (await client.get("/api/v1/executions/" + run["id"], headers=headers)).json()[
            "status"
        ] == "succeeded"


async def test_queued_cancellation_prevents_steps():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, run = await prepare(client, ["trigger.manual", "action.record_result"])
        result = await client.post("/api/v1/executions/" + run["id"] + "/cancel", headers=headers)
        assert result.json()["status"] == "cancelled"
        await engine.process_execution(session_factory, UUID(run["id"]))
        async with session_factory() as session:
            assert (
                await session.scalar(
                    select(ExecutionStep).where(ExecutionStep.execution_id == UUID(run["id"]))
                )
                is None
            )


async def test_stale_external_intent_fails_uncertain_without_resending(monkeypatch):
    from app.workflows.registry import REGISTRY, NodeSpec

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, run = await prepare(client, ["trigger.manual", "action.record_result"])
        run_id = UUID(run["id"])
        await engine.process_execution(session_factory, run_id)
        original = REGISTRY["action.record_result"]
        monkeypatch.setitem(
            REGISTRY,
            original.type,
            NodeSpec(
                original.type,
                original.title,
                original.config,
                original.category,
                side_effect="external",
            ),
        )
        async with session_factory() as session:
            saved = await session.get(WorkflowExecution, run_id)
            saved.status = "running"
            saved.node_attempt = 1
            saved.lease_token = uuid4()
            saved.lease_until = now() - timedelta(seconds=1)
            session.add(
                ExecutionStep(
                    execution_id=run_id,
                    node_id="node_1",
                    node_type="action.record_result",
                    attempt_number=1,
                )
            )
            await session.commit()
        await engine.process_execution(session_factory, run_id)
        result = (await client.get("/api/v1/executions/" + run["id"], headers=headers)).json()
        assert result["status"] == "failed"
        assert result["error_code"] == "UNCERTAIN_EXTERNAL_RESULT"
        assert (
            await client.post("/api/v1/executions/" + run["id"] + "/retry", headers=headers)
        ).status_code == 409


async def test_expired_checkpoint_cancels_without_running_next_node():
    from app.execution.worker import expire_approvals
    from app.models import ApprovalRequest

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, run = await prepare(
            client,
            ["trigger.manual", "action.request_approval", "action.record_result"],
            {1: {"kind": "continue"}},
        )
        run_id = UUID(run["id"])
        await engine.process_execution(session_factory, run_id)
        await engine.process_execution(session_factory, run_id)
        async with session_factory() as session:
            approval = await session.scalar(
                select(ApprovalRequest).where(ApprovalRequest.execution_id == run_id)
            )
            approval.expires_at = now() - timedelta(seconds=1)
            await session.commit()
        await expire_approvals(session_factory)
        await engine.process_execution(session_factory, run_id)
        result = (await client.get("/api/v1/executions/" + run["id"], headers=headers)).json()
        assert result["status"] == "cancelled"
        assert (await client.get("/api/v1/approvals", headers=headers)).json()["items"][0][
            "status"
        ] == "expired"


async def test_broker_failure_retains_outbox_for_later_publication(monkeypatch):
    from app.execution import worker
    from app.models import OutboxEntry

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        _, run = await prepare(client, ["trigger.manual", "action.record_result"])
        run_id = UUID(run["id"])

        def unavailable(*args, **kwargs):
            raise ConnectionError("This sensitive provider text must not be stored.")

        monkeypatch.setattr(worker.celery_app, "send_task", unavailable)
        await worker.dispatch_pending()
        async with session_factory() as session:
            outbox = await session.scalar(
                select(OutboxEntry).where(OutboxEntry.execution_id == run_id)
            )
            assert outbox.published_at is None
            assert outbox.last_error == "BROKER_UNAVAILABLE"
            outbox.available_at = now() - timedelta(seconds=1)
            await session.commit()
        sent = []
        monkeypatch.setattr(
            worker.celery_app, "send_task", lambda *args, **kwargs: sent.append(kwargs["args"])
        )
        await worker.dispatch_pending()
        assert [str(run_id)] in sent
        async with session_factory() as session:
            outbox = await session.scalar(
                select(OutboxEntry).where(OutboxEntry.execution_id == run_id)
            )
            assert outbox.published_at is not None


async def test_lead_created_dispatches_same_tenant_published_workflow_once():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, _ = await prepare(client, ["trigger.lead_created", "action.record_result"])
        lead = await client.post(
            "/api/v1/leads",
            headers=headers,
            json={"name": "Fictional Buyer", "email": "fictional-buyer@example.com"},
        )
        assert lead.status_code == 201, lead.text
        runs = (await client.get("/api/v1/executions", headers=headers)).json()["items"]
        automatic = [run for run in runs if run["trigger_type"] == "lead_created"]
        assert len(automatic) == 1
        assert automatic[0]["mode"] == "live"
        assert automatic[0]["context"]["lead_id"] == lead.json()["id"]
        assert automatic[0]["correlation_id"] == lead.headers["X-Request-ID"]
        await client.patch(
            "/api/v1/leads/" + lead.json()["id"],
            headers=headers,
            json={"company": "Changed company"},
        )
        assert (await client.get("/api/v1/executions", headers=headers)).json()["total"] == 2


async def test_scheduler_coalesces_missed_intervals_and_honors_pause():
    from app.execution.triggers import schedule_due
    from app.models import Workflow

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, run = await prepare(
            client, ["trigger.scheduled", "action.record_result"], {0: {"interval_minutes": 1}}
        )
        async with session_factory() as session:
            workflow = await session.get(Workflow, UUID(run["workflow_id"]))
            workflow.scheduled_next_run_at = now() - timedelta(hours=1)
            await session.commit()
        await schedule_due(session_factory)
        await schedule_due(session_factory)
        runs = (await client.get("/api/v1/executions", headers=headers)).json()["items"]
        scheduled = [r for r in runs if r["trigger_type"] == "scheduled"]
        assert len(scheduled) == 1
        assert scheduled[0]["mode"] == "live"
        async with session_factory() as session:
            workflow = await session.get(Workflow, UUID(run["workflow_id"]))
            assert workflow.scheduled_next_run_at > now()
            workflow.status = "paused"
            workflow.scheduled_next_run_at = now() - timedelta(minutes=1)
            await session.commit()
        await schedule_due(session_factory)
        assert (await client.get("/api/v1/executions", headers=headers)).json()["total"] == 2
