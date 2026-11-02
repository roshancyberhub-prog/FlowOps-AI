import httpx
import pytest

from app.integrations.security import (
    post_webhook,
    signature,
    validate_destination,
    verify_signature,
)


def test_signatures_bind_exact_body_timestamp_and_endpoint():
    key = "operator-test-key-that-is-long-enough"
    signed = signature(key, "endpoint-one", 1000, b'{"a":1}')
    assert verify_signature(key, "endpoint-one", "1000", signed, b'{"a":1}', 1001)
    assert not verify_signature(key, "endpoint-two", "1000", signed, b'{"a":1}', 1001)
    assert not verify_signature(key, "endpoint-one", "1000", signed, b'{"a":2}', 1001)
    assert not verify_signature(key, "endpoint-one", "1000", signed, b'{"a":1}', 1400)
    assert not verify_signature(key, "endpoint-one", "invalid", signed, b'{"a":1}', 1001)


@pytest.mark.parametrize(
    "url,ips",
    [
        ("http://hooks.example.test/x", ["8.8.8.8"]),
        ("https://user:pass@hooks.example.test/x", ["8.8.8.8"]),
        ("https://hooks.example.test/x?token=value", ["8.8.8.8"]),
        ("https://hooks.example.test:8443/x", ["8.8.8.8"]),
        ("https://other.example.test/x", ["8.8.8.8"]),
        ("https://hooks.example.test/x", ["127.0.0.1"]),
        ("https://hooks.example.test/x", ["8.8.8.8", "10.0.0.1"]),
        ("https://hooks.example.test/x", ["::ffff:127.0.0.1"]),
    ],
)
async def test_unsafe_destinations_are_rejected(url, ips):
    async def resolver(host):
        return ips

    with pytest.raises(ValueError):
        await validate_destination(url, {"hooks.example.test"}, resolver)


async def test_dns_is_pinned_with_original_host_and_tls_name_and_no_redirects():
    async def resolver(host):
        return ["8.8.8.8"]

    seen = []

    async def handler(request):
        seen.append(request)
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    status = await post_webhook(
        "https://hooks.example.test/path",
        {"hooks.example.test"},
        b"{}",
        {},
        resolver,
        httpx.MockTransport(handler),
    )
    assert status == 302 and len(seen) == 1
    assert seen[0].url.host == "8.8.8.8"
    assert seen[0].headers["host"] == "hooks.example.test"
    assert seen[0].extensions["sni_hostname"] == "hooks.example.test"
