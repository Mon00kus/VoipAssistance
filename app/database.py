import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger("voiceassistant")

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_FALLBACK_URL = f"sqlite+aiosqlite:///{(BASE_DIR / 'voiceassistant.db').as_posix()}"


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    connect_args = {}
    if url.startswith("postgresql"):
        connect_args = {"timeout": 5, "command_timeout": 10}
    return create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine = _make_engine(settings.DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_db_url_in_use = settings.DATABASE_URL


async def init_database() -> str:
    """Create tables, falling back to a local SQLite file if the configured DB is unreachable."""
    global engine, async_session, _db_url_in_use

    # Import models so they register on Base.metadata before create_all runs.
    from app import models  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Connected to database: %s", _db_url_in_use)
        return _db_url_in_use
    except Exception as exc:  # noqa: BLE001 - we want to surface and recover from any driver error
        logger.warning("Could not reach %s (%s)", settings.DATABASE_URL, type(exc).__name__)

    await engine.dispose()
    engine = _make_engine(SQLITE_FALLBACK_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _db_url_in_use = SQLITE_FALLBACK_URL

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.warning("Falling back to local SQLite database: %s", SQLITE_FALLBACK_URL)
    return _db_url_in_use


async def get_db():
    async with async_session() as session:
        yield session


async def healthcheck() -> dict:
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "url": _db_url_in_use}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "database": "unreachable", "error": type(exc).__name__}
