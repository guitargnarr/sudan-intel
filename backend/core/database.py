"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.core.config import settings

is_sqlite = "sqlite" in settings.DATABASE_URL


def _build_psycopg_url(url):
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


if "sqlite" in settings.DATABASE_URL:
    if "aiosqlite" not in settings.DATABASE_URL:
        db_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        db_url = settings.DATABASE_URL

    engine = create_async_engine(db_url, echo=False, future=True)
    sync_url = db_url.replace("+aiosqlite", "")
    sync_engine = create_engine(sync_url, echo=False)
else:
    pg_url = _build_psycopg_url(settings.DATABASE_URL)
    engine = create_async_engine(
        pg_url, echo=False, future=True, pool_size=10, max_overflow=20,
    )
    sync_pg_url = _build_psycopg_url(settings.DATABASE_URL)
    sync_engine = create_engine(sync_pg_url, echo=False)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)

SessionLocal = sessionmaker(sync_engine, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
