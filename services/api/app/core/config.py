from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    database_url: PostgresDsn
    redis_url: RedisDsn
    web_origin: str = "http://localhost:3000"
    session_lifetime_seconds: int = Field(default=3600, ge=300, le=86400)
    allow_public_registration: bool = False
    demo_retry_failure: bool = False
    ai_provider: Literal["disabled", "mock"] = "disabled"
    email_provider: Literal["disabled", "mock"] = "disabled"
    max_step_attempts: int = Field(default=3, ge=1, le=5)
    execution_max_active_seconds: int = Field(default=600, ge=30, le=3600)
    webhook_signing_key: SecretStr = SecretStr("")
    webhook_allowed_hosts: str = ""
    approval_ttl_hours: int = Field(default=72, ge=1, le=168)


@lru_cache
def get_settings() -> Settings:
    return Settings()
