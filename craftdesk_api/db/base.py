"""CraftDesk API — async SQLAlchemy engine and session factory for Neon.tech PostgreSQL."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from craftdesk_api.core.config import settings

# ── Engine ───────────────────────────────────────────────────────────────────
# SQLite (used in tests) does not support pool_size/max_overflow — guard against it.
_is_sqlite = settings.database_url.startswith("sqlite")
_engine_kwargs: dict[str, object] = {
    "echo": settings.debug,
    "pool_pre_ping": not _is_sqlite,  # aiosqlite doesn't support pool_pre_ping
}
if not _is_sqlite:
    # pool_pre_ping drops stale connections — important for Neon.tech auto-suspend
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.database_url, **_engine_kwargs)

# ── Session factory ──────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative base for all ORM models ──────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all CraftDesk SQLAlchemy ORM models."""


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session; roll back on error, close on exit.

    Usage in route handlers::

        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
