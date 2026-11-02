import asyncio
import hashlib
import hmac
import ipaddress
import re
import socket
from collections.abc import Awaitable, Callable

import httpx

Resolver = Callable[[str], Awaitable[list[str]]]


def signature(key: str, endpoint: str, timestamp: int, body: bytes) -> str:
    derived = hmac.digest(key.encode(), endpoint.encode(), "sha256")
    return (
        "sha256="
        + hmac.new(derived, str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
    )


def verify_signature(
    key: str, endpoint: str, timestamp: str, signed: str, body: bytes, now: int
) -> bool:
    if not re.fullmatch(r"[0-9]{1,12}", timestamp) or not re.fullmatch(
        r"sha256=[a-f0-9]{64}", signed
    ):
        return False
    value = int(timestamp)
    return abs(now - value) <= 300 and hmac.compare_digest(
        signature(key, endpoint, value, body), signed
    )


async def resolve(host: str) -> list[str]:
    records = await asyncio.wait_for(
        asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM), 3
    )
    return list({str(record[4][0]) for record in records})


async def validate_destination(
    url: str, allowed: set[str], resolver: Resolver = resolve
) -> tuple[httpx.URL, str]:
    parsed = httpx.URL(url)
    if (
        parsed.scheme != "https"
        or parsed.port not in {None, 443}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.host not in allowed
    ):
        raise ValueError(
            "Choose an allowlisted HTTPS destination without credentials or query strings."
        )
    addresses = await resolver(parsed.host)
    if not addresses or len(addresses) > 16:
        raise ValueError("The destination has no acceptable DNS records.")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global or ip.is_multicast or ip.is_unspecified:
            raise ValueError("Private, reserved and local destinations are blocked.")
    return parsed, addresses[0]


async def post_webhook(
    url: str,
    allowed: set[str],
    body: bytes,
    headers: dict[str, str],
    resolver: Resolver = resolve,
    transport: httpx.AsyncBaseTransport | None = None,
) -> int:
    parsed, address = await validate_destination(url, allowed, resolver)
    async with httpx.AsyncClient(
        transport=transport, trust_env=False, follow_redirects=False, timeout=10
    ) as client:
        async with client.stream(
            "POST",
            parsed.copy_with(host=address),
            content=body,
            headers={**headers, "Host": parsed.host},
            extensions={"sni_hostname": parsed.host},
        ) as response:
            return response.status_code
