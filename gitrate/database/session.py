"""Session management for the SQLAlchemy async engine.

Why this module exists
----------------------
``gitrate/api/dashboard.py`` and ``gitrate/api/trends.py`` imported
``AsyncSessionLocal`` from the ORM module, but no such object was ever defined
there, so importing the FastAPI application raised ``ImportError`` and the whole
platform failed to start (see ``docs/IMPLEMENTATION_GAP_ANALYSIS.md``, P0-1).

This module provides the missing session factory with *lazy* engine creation so
importing the application never requires a reachable database.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from gitrate.utils.config import settings

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Return (creating if necessary) the process-wide async engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.db_echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )
        logger.debug("Created async database engine")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return (creating if necessary) the process-wide session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


class _SessionContext:
    """Minimal async context manager yielding a session (``async with`` support)."""

    def __init__(self) -> None:
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        self._session = get_session_factory()()
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


def AsyncSessionLocal() -> _SessionContext:
    """Return an async context manager that yields a database session.

    Mirrors the ``async_sessionmaker()`` calling convention used by the API
    routers (``async with AsyncSessionLocal() as session:``).
    """
    return _SessionContext()


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session."""
    async with get_session_factory()() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose of the engine and cached session factory (used on shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def set_engine(engine: AsyncEngine) -> None:
    """Override the process-wide engine (used by tests to inject a test engine)."""
    global _engine, _session_factory
    _engine = engine
    _session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
