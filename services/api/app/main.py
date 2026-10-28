import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from pythonjsonlogger.json import JsonFormatter
from starlette.responses import Response

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.getLogger("flowops").addHandler(handler)

app = FastAPI(title="FlowOps AI", version="0.1.0")


@app.middleware("http")
async def request_context(request: Request, call_next) -> Response:
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/v1/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}
