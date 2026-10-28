from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.test_leads import account

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("isolate_rate_limit_keys")]


async def test_publish_freezes_graph_and_rejects_stale_drafts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await account(client, f"workflow-{uuid4()}@example.com")
        org = (await client.post("/api/v1/organizations", json={"name": "Workflow team"})).json()
        headers = {"X-Organization-ID": org["id"]}
        created = await client.post(
            "/api/v1/workflows", headers=headers, json={"name": "First workflow"}
        )
        assert created.status_code == 201, created.text
        workflow = created.json()
        path = f"/api/v1/workflows/{workflow['id']}"
        published = await client.post(
            path + "/publish", headers=headers, json={"expected_revision": workflow["revision"]}
        )
        assert published.status_code == 200, published.text
        version_id = published.json()["current_version_id"]
        revision = published.json()["revision"]
        original = (await client.get(path + f"/versions/{version_id}", headers=headers)).json()
        from sqlalchemy import update
        from sqlalchemy.exc import DBAPIError

        from app.db.session import session_factory
        from app.models import WorkflowVersion

        async with session_factory() as session:
            with pytest.raises(DBAPIError):
                await session.execute(
                    update(WorkflowVersion)
                    .where(WorkflowVersion.id == UUID(version_id))
                    .values(graph_definition={})
                )
            await session.rollback()
        graph = workflow["draft_graph"]
        graph["nodes"][-1]["label"] = "Changed draft"
        saved = await client.patch(
            path,
            headers=headers,
            json={
                "expected_revision": revision,
                "graph": graph,
            },
        )
        assert saved.status_code == 200, saved.text
        assert (
            await client.get(path + f"/versions/{version_id}", headers=headers)
        ).json() == original
        assert (
            await client.patch(
                path,
                headers=headers,
                json={
                    "expected_revision": revision,
                    "name": "Stale overwrite",
                },
            )
        ).status_code == 409
        graph["edges"].append(
            {"source": graph["nodes"][-1]["id"], "target": graph["nodes"][0]["id"]}
        )
        saved = await client.patch(
            path,
            headers=headers,
            json={
                "expected_revision": saved.json()["revision"],
                "graph": graph,
            },
        )
        invalid = await client.post(
            path + "/publish", headers=headers, json={"expected_revision": saved.json()["revision"]}
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["details"]
        assert (await client.get(path, headers=headers)).json()["current_version_id"] == version_id
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
            await account(other, f"other-workflow-{uuid4()}@example.com")
            assert (await other.get(path, headers=headers)).status_code == 403
