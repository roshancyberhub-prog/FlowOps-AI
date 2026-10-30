from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.base import now
from app.db.session import session_factory
from app.main import app
from app.models import WorkflowExecution
from tests.test_leads import account

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("isolate_rate_limit_keys")]


async def test_overview_uses_scoped_database_counts_and_zero_filled_utc_days():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await account(client, f"analytics-{uuid4()}@example.com")
        org = (await client.post("/api/v1/organizations", json={"name": "Analytics"})).json()
        headers = {"X-Organization-ID": org["id"]}
        empty = (await client.get("/api/v1/analytics/overview", headers=headers)).json()
        assert empty["executions"] == empty["active_leads"] == 0
        assert empty["success_rate"] is None and len(empty["daily"]) == 7
        for index in range(2):
            lead = (
                await client.post(
                    "/api/v1/leads",
                    headers=headers,
                    json={"name": "Buyer", "email": f"buyer{index}@example.com"},
                )
            ).json()
        await client.delete("/api/v1/leads/" + lead["id"], headers=headers)
        workflow = (
            await client.post(
                "/api/v1/workflows", headers=headers, json={"name": "Metrics workflow"}
            )
        ).json()
        path = "/api/v1/workflows/" + workflow["id"]
        await client.post(
            path + "/publish", headers=headers, json={"expected_revision": workflow["revision"]}
        )
        for _ in range(3):
            result = await client.post(
                path + "/test-runs", headers={**headers, "Idempotency-Key": str(uuid4())}, json={}
            )
            assert result.status_code == 202, result.text
        async with session_factory() as session:
            runs = list(
                await session.scalars(
                    select(WorkflowExecution)
                    .where(WorkflowExecution.workflow_id == UUID(workflow["id"]))
                    .order_by(WorkflowExecution.created_at)
                )
            )
            runs[0].status, runs[0].active_duration_ms = "succeeded", 100
            runs[1].status, runs[1].active_duration_ms = "failed", 300
            runs[2].status, runs[2].created_at = "succeeded", now() - timedelta(days=8)
            await session.commit()
        data = (await client.get("/api/v1/analytics/overview", headers=headers)).json()
        assert data["executions"] == 2
        assert data["succeeded"] == data["failed"] == 1
        assert data["active_leads"] == data["active_workflows"] == 1
        assert data["success_rate"] == 50 and data["average_active_ms"] == 200
        assert (
            sum(point["succeeded"] + point["failed"] + point["other"] for point in data["daily"])
            == 2
        )
        assert len(data["recent_executions"]) == 2
        listed = (await client.get("/api/v1/workflows", headers=headers)).json()["items"][0]
        assert listed["execution_count"] == 3 and listed["last_execution_at"]
        health = (await client.get("/api/v1/execution-health", headers=headers)).json()
        assert health["executions_by_status"] == {"succeeded": 2, "failed": 1}
        assert health["pending_imports"] == 0 and health["webhooks_by_status"] == {}
        other = (
            await client.post("/api/v1/organizations", json={"name": "Separate analytics"})
        ).json()
        isolated = (
            await client.get(
                "/api/v1/analytics/overview", headers={"X-Organization-ID": other["id"]}
            )
        ).json()
        assert isolated["executions"] == isolated["active_leads"] == 0
        assert isolated["recent_executions"] == []


async def test_maintenance_removes_expired_sessions_and_keeps_current_session():
    from app.execution.worker import cleanup_expired_sessions
    from app.models import AccessToken, Membership

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await account(client, f"maintenance-{uuid4()}@example.com")
        org = (
            await client.post("/api/v1/organizations", json={"name": "Session maintenance"})
        ).json()
        expired = str(uuid4())
        async with session_factory() as session:
            member = await session.scalar(
                select(Membership).where(Membership.organization_id == UUID(org["id"]))
            )
            session.add(
                AccessToken(
                    token=expired, user_id=member.user_id, created_at=now() - timedelta(days=2)
                )
            )
            await session.commit()
        await cleanup_expired_sessions(session_factory)
        async with session_factory() as session:
            assert await session.get(AccessToken, expired) is None
        assert (await client.get("/api/v1/users/me")).status_code == 200
