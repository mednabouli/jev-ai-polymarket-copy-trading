"""
Database Module

Async PostgreSQL access layer using asyncpg.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
import structlog
import asyncpg

logger = structlog.get_logger()


class Database:
    """Async PostgreSQL database wrapper"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        """Create connection pool"""
        self._pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("Database pool initialized")
    
    async def close(self) -> None:
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")
    
    async def fetch_all(
        self, query: str, values: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dicts"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, **values) if values else await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def fetch_one(
        self, query: str, values: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row as dict"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, **values) if values else await conn.fetchrow(query)
            return dict(row) if row else None
    
    async def fetch_val(
        self, query: str, values: Optional[Dict[str, Any]] = None, column: int = 0
    ) -> Any:
        """Fetch single value"""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, **values) if values else await conn.fetchval(query, column=column)
    
    async def execute(
        self, query: str, values: Optional[Dict[str, Any]] = None
    ) -> str:
        """Execute query and return status"""
        async with self._pool.acquire() as conn:
            return await conn.execute(query, **values) if values else await conn.execute(query)
    
    async def execute_many(
        self, query: str, values: List[Dict[str, Any]]
    ) -> None:
        """Execute query with multiple parameter sets"""
        async with self._pool.acquire() as conn:
            await conn.executemany(query, values)
    
    async def transaction(self):
        """Get a transaction context manager"""
        return self._pool.acquire()


# Global database instance (for dependency injection)
_db: Optional[Database] = None


def get_database() -> Database:
    """Get database instance"""
    if not _db:
        raise RuntimeError("Database not initialized")
    return _db
