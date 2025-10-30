"""
CoffeeBuddy Database Connection Manager
Handles PostgreSQL connection pooling and session management
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions with connection pooling"""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 0,
        pool_timeout: int = 30,
        echo: bool = False,
    ):
        """
        Initialize database manager with connection pooling

        Args:
            database_url: PostgreSQL connection string (asyncpg format)
            pool_size: Maximum number of connections in pool (default: 20)
            max_overflow: Maximum overflow connections (default: 0)
            pool_timeout: Connection timeout in seconds (default: 30)
            echo: Enable SQL query logging (default: False)
        """
        self.database_url = database_url
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            echo=echo,
            pool_pre_ping=True,  # Verify connections before use
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info(
            f"Database manager initialized with pool_size={pool_size}, "
            f"max_overflow={max_overflow}, pool_timeout={pool_timeout}s"
        )

    async def create_tables(self) -> None:
        """Create all tables (for testing/development only)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all tables (for testing/development only)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional database session

        Usage:
            async with db_manager.session() as session:
                result = await session.execute(query)
                await session.commit()
        """
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close database engine and connection pool"""
        await self.engine.dispose()
        logger.info("Database connection pool closed")

    async def health_check(self) -> bool:
        """
        Verify database connectivity

        Returns:
            True if database is reachable, False otherwise
        """
        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
```

```bash