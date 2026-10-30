from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings

MAX_REQUEST_BYTES = 1024 * 1024
RATE_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""


class RequestGuard:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith("/api/v1/health/"):
            await self.app(scope, receive, send)
            return
        status, code, message = 0, "", ""
        auth = scope["path"] in {"/api/v1/auth/register", "/api/v1/auth/session/login"}
        host = scope.get("client", ("unknown", 0))[0]
        try:
            async with Redis.from_url(str(get_settings().redis_url), socket_timeout=2) as redis:
                count = await redis.eval(
                    RATE_SCRIPT, 1, f"rate:{'auth' if auth else 'api'}:{host}", 900 if auth else 60
                )
            if int(count) > (10 if auth else 300):
                status, code, message = 429, "RATE_LIMITED", "Too many requests. Try again later."
        except (RedisError, OSError):
            status, code, message = (
                503,
                "RATE_LIMIT_UNAVAILABLE",
                "Service is temporarily unavailable.",
            )

        chunks: list[bytes] = []
        size = 0
        if not status:
            while True:
                event = await receive()
                if event["type"] == "http.disconnect":
                    return
                chunk = event.get("body", b"")
                size += len(chunk)
                if size > MAX_REQUEST_BYTES:
                    status, code, message = 413, "REQUEST_TOO_LARGE", "Request exceeds 1 MiB."
                    break
                chunks.append(chunk)
                if not event.get("more_body", False):
                    break
        if status:
            request_id = str(uuid4())
            response = JSONResponse(
                {
                    "error": {
                        "code": code,
                        "message": message,
                        "request_id": request_id,
                        "details": [],
                    }
                },
                status_code=status,
                headers={
                    "X-Request-ID": request_id,
                    "X-Content-Type-Options": "nosniff",
                    "Cache-Control": "no-store",
                    "Retry-After": "900" if auth else "60",
                },
            )
            await response(scope, receive, send)
            return

        consumed = False

        async def replay() -> Message:
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
