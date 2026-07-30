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


engine = create_async_engine(
    _normalize_async_url(settings.DATABASE_URL),
    echo=settings.DEBUG,
    # A pooled connection outlives the request that opened it, so it can be
    # closed by the far end — Render restarts Postgres for maintenance, and idle
    # TCP through a managed proxy gets reaped — while the pool still believes it
    # is good. Whoever checks it out next wears the error, having done nothing
    # wrong. `pool_pre_ping` spends one round-trip validating the connection at
    # checkout and transparently replaces a dead one, which turns that class of
    # failure into a hiccup nobody sees.
    #
    # This is not hypothetical. On 2026-07-30 at 06:57 UTC a single dropped
    # connection produced three separate user-visible failures: a 500 on
    # `GET /documenti/{id}/preview` (`InterfaceError: connection is closed`) and
    # two failed document generations in the Celery worker
    # (`ConnectionDoesNotExistError: connection was closed in the middle of
    # operation`). Only the worker had a net — `document_tasks` retries the
    # status reset on a fresh session so the row is not stranded `in_progress` —
    # and a customer who has paid for a document should not have to click
    # "Genera" again because a TCP connection went stale overnight.
    pool_pre_ping=True,
    # Retire connections well before an upstream idle timeout can, so the
    # pre-ping above is a backstop rather than the primary defence.
    pool_recycle=300,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
