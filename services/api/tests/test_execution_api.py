from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.db.session import session_factory
from app.main import app
from app.models import OutboxEntry
from tests.test_leads import account

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("isolate_rate_limit_keys")]


async def test_run_acceptance_is_durable_and_idempotent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await account(client, f"execution-{uuid4()}@example.com")
        org = (await client.post("/api/v1/organizations", json={"name": "Executions"})).json()
        headers = {"X-Organization-ID": org["id"]}
        workflow = (
            await client.post(
                "/api/v1/workflows", headers=headers, json={"name": "Record an event"}
            )
        ).json()
        path = f"/api/v1/workflows/{workflow['id']}"
        published = await client.post(
            path + "/publish", headers=headers, json={"expected_revision": workflow["revision"]}
        )
        assert published.status_code == 200, published.text
        headers["Idempotency-Key"] = str(uuid4())
        first = await client.post(path + "/test-runs", headers=headers, json={})
        assert first.status_code == 202, first.text
        execution = first.json()
        assert execution["status"] == "queued"
        assert execution["workflow_version_id"] == published.json()["current_version_id"]
        second = await client.post(path + "/test-runs", headers=headers, json={})
        assert second.status_code == 200
        assert second.json()["id"] == execution["id"]
        conflict = await client.post(
            path + "/test-runs",
            headers=headers,
            json={"sample_lead": {"name": "Different input", "email": "sample@example.com"}},
        )
        assert conflict.status_code == 409
        async with session_factory() as session:
            from uuid import UUID

            total = await session.scalar(
                select(func.count())
                .select_from(OutboxEntry)
                .where(OutboxEntry.execution_id == UUID(execution["id"]))
            )
            assert total == 1
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
            await account(other, f"other-execution-{uuid4()}@example.com")
            assert (
                await other.get(f"/api/v1/executions/{execution['id']}", headers=headers)
            ).status_code == 403
