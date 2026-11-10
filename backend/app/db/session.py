import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> AsyncEngine:
    """The single place where engine/pool behaviour is configured."""
    settings = get_settings()
    return create_async_engine(
        settings.async_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,
        connect_args={
            "timeout": settings.db_connect_timeout_seconds,
            "statement_cache_size": settings.db_statement_cache_size,
        },
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Request-scoped session. Reads need no commit; failed work is rolled back and closed."""
    async with get_sessionmaker()() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
        get_engine.cache_clear()
        get_sessionmaker.cache_clear()
