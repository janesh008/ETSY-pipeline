"""pytest conftest — set required CraftDesk env vars and shared async client fixture."""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

# Set env vars BEFORE any craftdesk_api module is imported.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-pytest-only-32bytes!!")
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("DEBUG", "true")

from craftdesk_api.main import app
from craftdesk_api.db.base import Base, get_db


@pytest.fixture()
def client():
    """Create a TestClient backed by an async in-memory aiosqlite database."""
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestSession = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _create() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

    async def _drop() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()

    asyncio.run(_drop())
