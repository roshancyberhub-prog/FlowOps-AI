from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.authentication.strategy.db import DatabaseStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import InvalidPasswordException
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from pydantic import Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.models import AccessToken, User


class UserRead(schemas.BaseUser[UUID]):
    display_name: str


class UserCreate(schemas.BaseUserCreate):
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


async def get_user_db(session: AsyncSession = Depends(get_session)) -> AsyncIterator:
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    async def validate_password(self, password: str, user: object) -> None:
        if len(password) < 12 or len(password) > 128:
            raise InvalidPasswordException(reason="Use a password between 12 and 128 characters.")


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncIterator[UserManager]:
    yield UserManager(user_db)


async def get_token_db(session: AsyncSession = Depends(get_session)) -> AsyncIterator:
    yield SQLAlchemyAccessTokenDatabase(session, AccessToken)


def get_strategy(
    token_db: SQLAlchemyAccessTokenDatabase = Depends(get_token_db),
) -> DatabaseStrategy:
    return DatabaseStrategy(token_db, lifetime_seconds=get_settings().session_lifetime_seconds)


transport = CookieTransport(
    cookie_name="flowops_session",
    cookie_max_age=get_settings().session_lifetime_seconds,
    cookie_secure=get_settings().app_env == "production",
    cookie_httponly=True,
    cookie_samesite="lax",
)
backend = AuthenticationBackend(name="session", transport=transport, get_strategy=get_strategy)
users = FastAPIUsers[User, UUID](get_user_manager, [backend])
current_user = users.current_user(active=True)
