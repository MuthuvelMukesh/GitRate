"""Database and cache initialization."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from core.database import get_database_engine, get_session_factory, SessionLocal, init_db
from core.cache import init_cache, shutdown_cache, cache

logger = logging.getLogger(__name__)


class AppState:
    """Application state management."""
    
    def __init__(self):
        """Initialize application state."""
        self.db_engine: Optional[AsyncEngine] = None
        self.db_session_factory: Optional[object] = None
        self.cache_initialized = False


# Global app state
app_state = AppState()


async def initialize_app():
    """Initialize all app resources (database, cache, etc)."""
    
    logger.info("🚀 Initializing application resources...")
    
    try:
        # Initialize database
        logger.info("📦 Initializing database...")
        await init_db()
        logger.info("✅ Database initialized")
        
        # Initialize cache
        logger.info("💾 Initializing cache...")
        await init_cache()
        app_state.cache_initialized = True
        logger.info("✅ Cache initialized")
        
        logger.info("🎉 All resources initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize resources: {e}", exc_info=True)
        raise


async def shutdown_app():
    """Shutdown all app resources."""
    
    logger.info("🛑 Shutting down application resources...")
    
    try:
        # Shutdown cache
        if app_state.cache_initialized:
            logger.info("Shutting down cache...")
            await shutdown_cache()
            logger.info("✅ Cache shutdown")
        
        # Database cleanup (if needed)
        if app_state.db_engine:
            logger.info("Closing database connections...")
            await app_state.db_engine.dispose()
            logger.info("✅ Database connections closed")
        
        logger.info("✅ All resources shutdown successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


@asynccontextmanager
async def get_db_session():
    """
    Context manager for database sessions.
    
    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
    """
    
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
