"""Tests for the database adapter without PostgreSQL access."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from database import Database


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakePool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return FakeAcquire(self.connection)


@pytest.mark.asyncio
async def test_fetch_one_returns_dict():
    connection = AsyncMock()
    connection.fetchrow.return_value = {"id": 1, "name": "whale"}
    db = Database("postgresql://unused")
    db._pool = FakePool(connection)

    result = await db.fetch_one("SELECT id, name FROM wallets")

    assert result == {"id": 1, "name": "whale"}
    connection.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_all_returns_list_of_dicts():
    connection = AsyncMock()
    connection.fetch.return_value = [{"id": 1}, {"id": 2}]
    db = Database("postgresql://unused")
    db._pool = FakePool(connection)

    result = await db.fetch_all("SELECT id FROM wallets")

    assert result == [{"id": 1}, {"id": 2}]
    connection.fetch.assert_awaited_once()
