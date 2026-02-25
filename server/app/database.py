import os
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _normalize_url(url: str) -> tuple[str, bool]:
    """Ensure the URL uses the asyncpg driver and extract sslmode."""
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    use_ssl = "sslmode" in params and params["sslmode"] != ["disable"]
    params.pop("sslmode", None)
    cleaned = parsed._replace(query=urlencode(params, doseq=True))
    return urlunparse(cleaned), use_ssl


DATABASE_URL, _use_ssl = _normalize_url(
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://toyuser:toypass@localhost:5432/toydb",
    )
)

_connect_args = {"ssl": True} if _use_ssl else {}
engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session
