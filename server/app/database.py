import os
import ssl
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _normalize_url(url: str | None) -> str | None:
    """Ensure the URL uses the asyncpg driver."""
    if not url:
        return None
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


def _build_database_url_from_parts() -> str | None:
    host = os.environ.get("DATABASE_HOST")
    name = os.environ.get("DATABASE_NAME")
    username = os.environ.get("DATABASE_USERNAME")
    password = os.environ.get("DATABASE_PASSWORD")
    if not all([host, name, username, password]):
        return None
    return f"postgresql+asyncpg://{username}:{password}@{host}/{name}"


def _build_ssl_connect_args() -> dict[str, Any]:
    ssl_mode = os.environ.get("DATABASE_SSL_MODE", "").strip().lower()
    ssl_root_cert = os.environ.get("DATABASE_SSL_ROOT_CERT")

    if not ssl_mode:
        if ssl_root_cert:
            raise ValueError("DATABASE_SSL_ROOT_CERT requires DATABASE_SSL_MODE")
        return {}

    if ssl_mode == "disable":
        return {}

    if ssl_mode in {"prefer", "allow"}:
        if ssl_root_cert:
            raise ValueError(
                "DATABASE_SSL_ROOT_CERT is only supported with "
                "DATABASE_SSL_MODE=require, verify-ca, or verify-full"
            )
        return {"ssl": ssl_mode}

    if ssl_mode == "require":
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return {"ssl": context}

    if ssl_mode in {"verify-ca", "verify-full"}:
        context = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH,
            cafile=ssl_root_cert or None,
        )
        context.check_hostname = ssl_mode == "verify-full"
        return {"ssl": context}

    raise ValueError(f"Unsupported DATABASE_SSL_MODE: {ssl_mode}")


DATABASE_URL = _normalize_url(
    os.environ.get("DATABASE_URL") or _build_database_url_from_parts()
)
CONNECT_ARGS = _build_ssl_connect_args()

engine = (
    create_async_engine(DATABASE_URL, echo=False, connect_args=CONNECT_ARGS)
    if DATABASE_URL
    else None
)
async_session = (
    async_sessionmaker(engine, expire_on_commit=False) if engine is not None else None
)


def is_database_configured() -> bool:
    return async_session is not None


async def get_db() -> AsyncGenerator[AsyncSession]:
    if async_session is None:
        raise RuntimeError("DATABASE_URL is not configured")
    async with async_session() as session:
        yield session
