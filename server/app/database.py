import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

def _normalize_url(url: str) -> str:
    """Ensure the URL uses the asyncpg driver."""
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


DATABASE_URL = _normalize_url(
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://toyuser:toypass@localhost:5432/toydb",
    )
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session
