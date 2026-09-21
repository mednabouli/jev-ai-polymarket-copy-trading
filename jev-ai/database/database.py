"""Database connection and query helpers."""

from typing import List, Dict, Any, Optional
import structlog
import psycopg
from psycopg import AsyncConnection

logger = structlog.get_logger()


class Database:
    """Async PostgreSQL database client."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool: Optional[AsyncConnection] = None

    async def initialize(self) -> None:
        """Initialize database connection and run migrations."""
        logger.info("Connecting to database", url=self.database_url)
        self._pool = await psycopg.AsyncConnection.connect(self.database_url)
        logger.info("Database connected")

        from database.migrations import run_migrations
        await run_migrations(self)
        logger.info("Database migrations completed")

    async def close(self) -> None:
        """Close database connection."""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection closed")

    async def execute(self, query: str, parameters: Dict[str, Any]) -> None:
        """Execute a query with parameters."""
        if not self._pool:
            raise RuntimeError("Database not initialized")

        async with self._pool.cursor() as cursor:
            await cursor.execute(query, parameters)
            await self._pool.commit()

    async def execute_returning(self, query: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute an INSERT ... ON CONFLICT ... RETURNING query."""
        if not self._pool:
            raise RuntimeError("Database not initialized")

        async with self._pool.cursor() as cursor:
            await cursor.execute(query, parameters)
            row = await cursor.fetchone()
            await self._pool.commit()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    async def fetch_one(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row as a dictionary."""
        if not self._pool:
            raise RuntimeError("Database not initialized")

        async with self._pool.cursor() as cursor:
            await cursor.execute(query, parameters or {})
            row = await cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    async def fetch_all(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch all rows as a list of dictionaries."""
        if not self._pool:
            raise RuntimeError("Database not initialized")

        async with self._pool.cursor() as cursor:
            await cursor.execute(query, parameters or {})
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
