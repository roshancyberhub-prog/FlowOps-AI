import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def account(client, email):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Fictional-Test-Passphrase-42",
            "display_name": "Test user",
        },
    )
    assert response.status_code == 201, response.text
    response = await client.post(
        "/api/v1/auth/session/login",
        data={
            "username": email,
            "password": "Fictional-Test-Passphrase-42",
        },
    )
    assert response.status_code == 204, response.text


@pytest.mark.integration
async def test_leads_persist_and_cross_tenant_access_is_rejected():
    from uuid import uuid4

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as first:
        await account(first, f"first-{uuid4()}@example.com")
        response = await first.post("/api/v1/organizations", json={"name": "First workspace"})
        assert response.status_code == 201, response.text
        organization = response.json()["id"]
        headers = {"X-Organization-ID": organization}
        response = await first.post(
            "/api/v1/leads",
            headers=headers,
            json={
                "name": "Sample buyer",
                "email": " Buyer@Example.com ",
                "company": "Example",
            },
        )
        assert response.status_code == 201, response.text
        lead = response.json()
        assert lead["email"] == "buyer@example.com"
        assert (await first.get(f"/api/v1/leads/{lead['id']}", headers=headers)).status_code == 200
        duplicate = await first.post(
            "/api/v1/leads",
            headers=headers,
            json={
                "name": "Duplicate",
                "email": "buyer@example.com",
            },
        )
        assert duplicate.status_code == 409
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as second:
            await account(second, f"second-{uuid4()}@example.com")
            assert (await second.get("/api/v1/leads", headers=headers)).status_code == 403
            other = (await second.post("/api/v1/organizations", json={"name": "Second"})).json()
            other_headers = {"X-Organization-ID": other["id"]}
            assert (
                await second.get(f"/api/v1/leads/{lead['id']}", headers=other_headers)
            ).status_code == 404
        updated = await first.patch(
            f"/api/v1/leads/{lead['id']}", headers=headers, json={"company": "Updated"}
        )
        assert updated.json()["company"] == "Updated"
        assert (
            await first.delete(f"/api/v1/leads/{lead['id']}", headers=headers)
        ).status_code == 204
        assert (await first.get("/api/v1/leads", headers=headers)).json()["total"] == 0
        assert (await first.post("/api/v1/auth/session/logout")).status_code == 204
        assert (await first.get("/api/v1/users/me")).status_code == 401


async def test_anonymous_lead_access_is_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/leads")).status_code == 401
