import httpx
import pytest

from app.integrations.github import IntegrationError, repository
from app.integrations.worker import outcome, retry_delay
from app.schemas.integrations import GitHubConfig, WebhookConfig


async def test_github_response_is_filtered_and_fixed_host():
    def respond(request):
        assert request.url.host == "api.github.com"
        assert request.url.path == "/repos/octocat/Hello-World"
        return httpx.Response(
            200,
            json={
                "full_name": "octocat/Hello-World",
                "stargazers_count": 1,
                "forks_count": 2,
                "open_issues_count": 3,
                "default_branch": "main",
                "untrusted": "discard",
            },
        )

    result = await repository("octocat", "Hello-World", httpx.MockTransport(respond))
    assert "untrusted" not in result
    assert result["url"] == "https://github.com/octocat/Hello-World"


@pytest.mark.parametrize(
    ("status", "code"), [(404, "NOT_FOUND"), (429, "RATE_LIMITED"), (302, "PROVIDER_UNAVAILABLE")]
)
async def test_github_failures_are_safe_codes(status, code):
    with pytest.raises(IntegrationError) as exc:
        await repository(
            "octocat", "Hello-World", httpx.MockTransport(lambda request: httpx.Response(status))
        )
    assert exc.value.code == code


@pytest.mark.parametrize("name", ["../secret", "x?token=value", "https://evil.test", "x/y"])
def test_repo_paths_cannot_change_the_fixed_request(name):
    with pytest.raises(ValueError):
        GitHubConfig(owner=name, repo="repo")


def test_webhook_config_is_strict():
    with pytest.raises(ValueError):
        WebhookConfig(destination="https://example.com?secret=yes")
    with pytest.raises(ValueError):
        WebhookConfig(unknown=True)


def test_retry_requires_receiver_contract_and_is_bounded():
    assert outcome(200, False, False, 1) == "delivered"
    assert outcome(None, True, False, 1) == "uncertain"
    assert outcome(None, True, True, 1) == "retrying"
    assert outcome(503, False, False, 1) == "failed"
    assert outcome(503, False, True, 4) == "retrying"
    assert outcome(503, False, True, 5) == "failed"
    assert outcome(400, False, True, 1) == "failed"
    assert outcome(302, False, True, 1) == "failed"
    assert retry_delay(1) == 5 and retry_delay(9) == 300
