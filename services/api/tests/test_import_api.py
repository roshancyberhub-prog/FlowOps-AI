import asyncio
import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.db.base import now
from app.db.session import session_factory
from app.leads import import_worker
from app.main import app
from app.models import ImportJob, Lead, OutboxEntry
from tests.test_leads import account

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("isolate_rate_limit_keys")]
MAPPING = {"name": "name", "email": "email"}


async def setup(client):
    await account(client, f"import-{uuid4()}@example.com")
    org = (await client.post("/api/v1/organizations", json={"name": "Import team"})).json()
    return {"X-Organization-ID": org["id"], "Idempotency-Key": str(uuid4())}


async def upload(client, headers, data):
    return await client.post(
        "/api/v1/leads/imports",
        headers=headers,
        files={"file": ("fictional-leads.csv", data, "text/csv")},
        data={"column_mapping": json.dumps(MAPPING)},
    )


async def test_import_is_durable_idempotent_and_reports_invalid_and_duplicate_records():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await setup(client)
        existing = (
            await client.post(
                "/api/v1/leads",
                headers=headers,
                json={"name": "Existing", "email": "existing@example.com"},
            )
        ).json()
        await client.delete("/api/v1/leads/" + existing["id"], headers=headers)
        data = (
            b"name,email\nExisting,existing@example.com\nNew,new@example.com\n"
            b"Invalid,bad-email\nDuplicate,NEW@example.com\nOther,other@example.com\n"
        )
        preview = await client.post(
            "/api/v1/leads/imports/preview",
            headers=headers,
            files={"file": ("leads.csv", data, "text/csv")},
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["row_count"] == 5
        response = await upload(client, headers, data)
        assert response.status_code == 202, response.text
        job = response.json()
        assert job["status"] == "queued" and job["processed_rows"] == 0
        replay = await upload(client, headers, data)
        assert replay.status_code == 200 and replay.json()["id"] == job["id"]
        assert (
            await upload(client, headers, b"name,email\nDifferent,different@example.com\n")
        ).status_code == 409
        job_id = UUID(job["id"])
        async with session_factory() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(OutboxEntry)
                    .where(OutboxEntry.import_job_id == job_id)
                )
                == 1
            )
        await import_worker.process_import(session_factory, job_id)
        await import_worker.process_import(session_factory, job_id)
        result = (await client.get("/api/v1/leads/imports/" + job["id"], headers=headers)).json()
        assert result["status"] == "succeeded"
        assert (result["inserted_rows"], result["invalid_rows"], result["duplicate_rows"]) == (
            2,
            1,
            2,
        )
        assert result["processed_rows"] == 5
        assert (
            await client.get("/api/v1/leads/imports/" + job["id"] + "/errors", headers=headers)
        ).json()["total"] == 1
        assert (
            await client.get(
                "/api/v1/leads/imports/" + job["id"] + "/rows?status=duplicate", headers=headers
            )
        ).json()["total"] == 2
        async with session_factory() as session:
            stored = await session.get(ImportJob, job_id)
            assert stored.source_data is None
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(Lead)
                    .where(Lead.organization_id == UUID(headers["X-Organization-ID"]))
                )
                == 3
            )
        other = (
            await client.post("/api/v1/organizations", json={"name": "Other import team"})
        ).json()
        assert (
            await client.get(
                "/api/v1/leads/imports/" + job["id"] + "/rows",
                headers={"X-Organization-ID": other["id"]},
            )
        ).status_code == 404


async def test_import_batches_resume_and_duplicate_worker_messages_do_not_duplicate_leads(
    monkeypatch,
):
    monkeypatch.setattr(import_worker, "BATCH_SIZE", 2)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await setup(client)
        job = (
            await upload(
                client,
                headers,
                b"name,email\nOne,one@example.com\nTwo,two@example.com\nThree,three@example.com\n",
            )
        ).json()
        job_id = UUID(job["id"])
        await import_worker.process_import(session_factory, job_id)
        interim = (await client.get("/api/v1/leads/imports/" + job["id"], headers=headers)).json()
        assert interim["status"] == "running" and interim["processed_rows"] == 2
        await asyncio.gather(
            *(import_worker.process_import(session_factory, job_id) for _ in range(3))
        )
        final = (await client.get("/api/v1/leads/imports/" + job["id"], headers=headers)).json()
        assert final["status"] == "succeeded" and final["inserted_rows"] == 3
        assert (
            await client.get("/api/v1/leads/imports/" + job["id"] + "/rows", headers=headers)
        ).json()["total"] == 3


async def test_failed_batch_rolls_back_leads_and_progress_before_retry(monkeypatch):
    original = import_worker.import_record

    async def fail_on_second(session, job, row):
        if row.number == 3:
            raise TimeoutError()
        return await original(session, job, row)

    monkeypatch.setattr(import_worker, "import_record", fail_on_second)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await setup(client)
        job = (
            await upload(client, headers, b"name,email\nOne,one@example.com\nTwo,two@example.com\n")
        ).json()
        job_id = UUID(job["id"])
        await import_worker.process_import(session_factory, job_id)
        failed = (await client.get("/api/v1/leads/imports/" + job["id"], headers=headers)).json()
        assert failed["status"] == "retrying" and failed["processed_rows"] == 0
        assert (await client.get("/api/v1/leads", headers=headers)).json()["total"] == 0
        monkeypatch.setattr(import_worker, "import_record", original)
        async with session_factory() as session:
            stored = await session.get(ImportJob, job_id)
            stored.next_run_at = now() - timedelta(seconds=1)
            await session.commit()
        await import_worker.process_import(session_factory, job_id)
        done = (await client.get("/api/v1/leads/imports/" + job["id"], headers=headers)).json()
        assert done["status"] == "succeeded" and done["inserted_rows"] == 2
