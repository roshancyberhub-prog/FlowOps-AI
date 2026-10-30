import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_live_is_available_without_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "url,route",
    [
        ("/api/v1/health/live?search=private@example.com", "/api/v1/health/live"),
        ("/api/v1/health/private@example.com", "_unmatched"),
    ],
)
async def test_request_log_excludes_query_and_unmatched_path_values(caplog, url, route):
    import logging

    logger = logging.getLogger("flowops")
    logger.addHandler(caplog.handler)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get(url)
        requests = [record for record in caplog.records if record.message == "request_completed"]
        assert requests
        assert requests[-1].duration_ms >= 0
        assert requests[-1].route == route
        assert requests[-1].path == route
        assert "private@example.com" not in str(requests[-1].__dict__)
    finally:
        logger.removeHandler(caplog.handler)
