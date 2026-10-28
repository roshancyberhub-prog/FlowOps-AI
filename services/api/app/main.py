import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis
from sqlalchemy import text
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response

from app.api.v1.executions import router as executions_router
from app.api.v1.leads import router as leads_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.workflows import router as workflows_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.security.auth import UserCreate, UserRead, backend, users
from app.security.http import RequestGuard

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_settings()
    yield
    await engine.dispose()


app = FastAPI(title="FlowOps AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestGuard)
app.include_router(users.get_register_router(UserRead, UserCreate), prefix="/api/v1/auth")
app.include_router(users.get_auth_router(backend), prefix="/api/v1/auth/session")
app.include_router(organizations_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(executions_router, prefix="/api/v1")


def error(
    request: Request, status: int, code: str, message: str, details: list[dict] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", ""),
                "details": details or [],
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return error(
            request,
            exc.status_code,
            str(exc.detail.get("code", f"HTTP_{exc.status_code}")),
            str(exc.detail.get("message", exc.detail.get("reason", "Request failed."))),
            exc.detail.get("details", []),
        )
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return error(request, exc.status_code, f"HTTP_{exc.status_code}", message)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
    return error(request, 422, "VALIDATION_ERROR", "Check the submitted fields.", details)


@app.middleware("http")
async def request_context(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request.state.request_id = str(uuid4())
    response: Response | None = None
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin != get_settings().web_origin:
            response = error(request, 403, "ORIGIN_REJECTED", "Request origin is not allowed.")
    if response is None:
        try:
            response = await call_next(request)
        except Exception as exc:
            logging.getLogger("flowops").error(
                "request_failed",
                extra={
                    "request_id": request.state.request_id,
                    "error_type": type(exc).__name__,
                },
            )
            response = error(request, 500, "INTERNAL_ERROR", "Unable to complete this request.")
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    logging.getLogger("flowops").info(
        "request_completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "request_id": request.state.request_id,
        },
    )
    return response


@app.get("/api/v1/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health/ready")
async def ready(request: Request) -> Response:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        async with Redis.from_url(str(get_settings().redis_url), socket_timeout=2) as redis:
            await redis.ping()
    except Exception:
        return error(request, 503, "NOT_READY", "Service is not ready.")
    return JSONResponse({"status": "ok"})
