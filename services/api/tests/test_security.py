import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.usefixtures("isolate_rate_limit_keys")


async def test_cross_site_mutation_is_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Attack"},
            headers={
                "Origin": "https://untrusted.example",
            },
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_REJECTED"


async def test_registration_validation_does_not_echo_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid",
                "password": "do-not-echo-this",
                "display_name": "Tester",
            },
        )
    assert response.status_code == 422
    assert "do-not-echo-this" not in response.text


async def test_large_request_is_rejected_before_parsing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/leads", content=b"x" * (1024 * 1024 + 1))
    assert response.status_code == 413


async def test_workflows_require_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/workflows")).status_code == 401


async def test_authentication_rate_limit_is_enforced():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(10):
            response = await client.post("/api/v1/auth/register", json={})
            assert response.status_code == 422
        response = await client.post("/api/v1/auth/register", json={})
    assert response.status_code == 429
    assert response.headers["retry-after"]


@pytest.mark.integration
async def test_viewer_can_read_but_cannot_modify_or_grant_permissions():
    from uuid import uuid4

    from tests.test_leads import account

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as owner:
        await account(owner, f"owner-{uuid4()}@example.com")
        org = (await owner.post("/api/v1/organizations", json={"name": "Permissions"})).json()
        headers = {"X-Organization-ID": org["id"]}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as viewer:
            email = f"viewer-{uuid4()}@example.com"
            await account(viewer, email)
            added = await owner.post(
                f"/api/v1/organizations/{org['id']}/members",
                headers=headers,
                json={"email": email, "role": "viewer"},
            )
            assert added.status_code == 201, added.text
            assert (await viewer.get("/api/v1/leads", headers=headers)).status_code == 200
            assert (
                await viewer.post(
                    "/api/v1/leads",
                    headers=headers,
                    json={
                        "name": "Attempt",
                        "email": "attempt@example.com",
                    },
                )
            ).status_code == 403
            assert (await viewer.get("/api/v1/audit", headers=headers)).status_code == 403
            assert (
                await viewer.patch(
                    f"/api/v1/organizations/{org['id']}/members/{added.json()['id']}",
                    headers=headers,
                    json={"role": "admin"},
                )
            ).status_code == 403
