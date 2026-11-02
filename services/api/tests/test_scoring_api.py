from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError

from app.db.session import session_factory
from app.execution.engine import process_execution
from app.main import app
from app.models import ScoringProfile
from app.workflows.templates import make_graph
from tests.test_leads import account
from tests.test_scoring import FIT

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("isolate_rate_limit_keys")]


async def test_profile_versions_are_immutable_and_published_workflow_pins_its_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await account(client, f"scoring-{uuid4()}@example.com")
        org = (await client.post("/api/v1/organizations", json={"name": "Scoring team"})).json()
        headers = {"X-Organization-ID": org["id"]}
        baseline = (await client.get("/api/v1/scoring-profiles/current", headers=headers)).json()
        assert baseline["version_number"] == 1
        lead_response = await client.post("/api/v1/leads", headers=headers, json=FIT)
        assert lead_response.status_code == 201, lead_response.text
        lead = lead_response.json()
        graph = make_graph(["trigger.manual", "action.score_lead", "action.record_result"])
        created = (
            await client.post(
                "/api/v1/workflows",
                headers=headers,
                json={"name": "Pinned scoring", "graph": graph.model_dump(by_alias=True)},
            )
        ).json()
        path = "/api/v1/workflows/" + created["id"]
        published = (
            await client.post(
                path + "/publish", headers=headers, json={"expected_revision": created["revision"]}
            )
        ).json()
        version = (
            await client.get(path + "/versions/" + published["current_version_id"], headers=headers)
        ).json()
        assert (
            version["graph_definition"]["nodes"][1]["config"]["scoring_profile"] == baseline["id"]
        )
        changed = {**baseline["configuration"], "title_weight": 5}
        new_profile = await client.post(
            "/api/v1/scoring-profiles",
            headers=headers,
            json={"name": "Lower title weight", "configuration": changed},
        )
        assert new_profile.status_code == 201, new_profile.text
        assert new_profile.json()["version_number"] == 2
        scored = await client.post(
            "/api/v1/leads/" + lead["id"] + "/score", headers=headers, json={}
        )
        assert scored.status_code == 200, scored.text
        assert scored.json()["score"] == 60 and scored.json()["score_profile_version"] == 2
        run = (
            await client.post(
                path + "/test-runs",
                headers={**headers, "Idempotency-Key": str(uuid4())},
                json={"lead_id": lead["id"]},
            )
        ).json()
        for _ in range(3):
            await process_execution(session_factory, UUID(run["id"]))
        result = (await client.get("/api/v1/executions/" + run["id"], headers=headers)).json()
        assert result["status"] == "succeeded"
        assert result["context"]["lead"]["score"] == 80
        assert result["context"]["lead"]["score_profile_version"] == 1
        assert (await client.get("/api/v1/leads/" + lead["id"], headers=headers)).json()[
            "score"
        ] == 60
        async with session_factory() as session:
            with pytest.raises(DBAPIError):
                await session.execute(
                    update(ScoringProfile)
                    .where(ScoringProfile.id == UUID(baseline["id"]))
                    .values(name="Forbidden mutation")
                )
            await session.rollback()
        edited = await client.patch(
            "/api/v1/leads/" + lead["id"], headers=headers, json={"job_title": "Analyst"}
        )
        assert edited.json()["scored_at"] is None
        assert edited.json()["score_reasons"] == []
        other = (
            await client.post("/api/v1/organizations", json={"name": "Other scoring team"})
        ).json()
        assert (
            await client.post(
                "/api/v1/leads/" + lead["id"] + "/score",
                headers={"X-Organization-ID": other["id"]},
                json={},
            )
        ).status_code == 404
