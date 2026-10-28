from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_live_is_available_without_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_request_log_excludes_query_values(caplog):
    import logging

    logger = logging.getLogger("flowops")
    logger.addHandler(caplog.handler)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/api/v1/health/live?search=private@example.com")
        requests = [record for record in caplog.records if record.message == "request_completed"]
        assert requests
        assert requests[-1].path == "/api/v1/health/live"
        assert "private@example.com" not in str(requests[-1].__dict__)
    finally:
        logger.removeHandler(caplog.handler)
