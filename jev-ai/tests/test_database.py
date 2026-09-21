"""Test suite for database module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from database import Database


class TestDatabase:
    """Tests for Database class."""

    @pytest.mark.asyncio
    async def test_fetch_one_returns_dict(self):
        """Test that fetch_one returns a dictionary."""
        mock_cursor = AsyncMock()
        mock_cursor.description = [("id", None), ("name", None)]
        mock_cursor.fetchone = AsyncMock(return_value=(1, "test"))
        
        mock_conn = AsyncMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor.__aenter__.return_value)
        mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        
        with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
            db = Database("postgresql://test")
            await db.initialize()
            
            result = await db.fetch_one("SELECT * FROM test WHERE id = :id", {"id": 1})
            
            assert result == {"id": 1, "name": "test"}
            await db.close()

    @pytest.mark.asyncio
    async def test_fetch_all_returns_list_of_dicts(self):
        """Test that fetch_all returns a list of dictionaries."""
        mock_cursor = AsyncMock()
        mock_cursor.description = [("id", None), ("name", None)]
        mock_cursor.fetchall = AsyncMock(return_value=[(1, "a"), (2, "b")])
        
        mock_conn = AsyncMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor.__aenter__.return_value)
        mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        
        with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
            db = Database("postgresql://test")
            await db.initialize()
            
            result = await db.fetch_all("SELECT * FROM test")
            
            assert result == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
            await db.close()

    @pytest.mark.asyncio
    async def test_execute_calls_commit(self):
        """Test that execute commits the transaction."""
        mock_cursor = AsyncMock()
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        
        mock_conn = AsyncMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        
        with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
            db = Database("postgresql://test")
            await db.initialize()
            
            await db.execute("INSERT INTO test VALUES (:id)", {"id": 1})
            
            assert mock_conn.commit.called
            await db.close()
