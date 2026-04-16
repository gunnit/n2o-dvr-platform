from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _normalize_async_url(url: str) -> str:
    # Render's managed Postgres hands us `postgres://…` or `postgresql://…`;
    # create_async_engine needs `postgresql+asyncpg://…`. Normalize once here
    # so both local dev and Render deployments work from the same config.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


engine = create_async_engine(_normalize_async_url(settings.DATABASE_URL), echo=settings.DEBUG)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
