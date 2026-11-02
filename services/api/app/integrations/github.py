import httpx
from pydantic import BaseModel, Field


class RepositoryData(BaseModel):
    full_name: str = Field(max_length=250)
    description: str | None = Field(default=None, max_length=2000)
    stargazers_count: int = Field(ge=0)
    forks_count: int = Field(ge=0)
    open_issues_count: int = Field(ge=0)
    default_branch: str = Field(max_length=200)


class IntegrationError(Exception):
    def __init__(self, code: str):
        self.code = code


async def repository(
    owner: str, repo: str, transport: httpx.AsyncBaseTransport | None = None
) -> dict:
    from app.schemas.integrations import GitHubConfig

    GitHubConfig(owner=owner, repo=repo)
    async with httpx.AsyncClient(
        transport=transport, timeout=10, follow_redirects=False, trust_env=False
    ) as client:
        async with client.stream(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "FlowOps-AI",
            },
        ) as response:
            if response.status_code != 200:
                raise IntegrationError(
                    "RATE_LIMITED"
                    if response.status_code in {403, 429}
                    else "NOT_FOUND"
                    if response.status_code == 404
                    else "PROVIDER_UNAVAILABLE"
                )
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > 256 * 1024:
                    raise IntegrationError("RESPONSE_TOO_LARGE")
            result = RepositoryData.model_validate_json(data).model_dump()
            result["url"] = f"https://github.com/{owner}/{repo}"
            return result
