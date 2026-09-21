"""Shared pytest fixtures for Jev AI."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


@pytest.fixture
def sample_wallet():
    """Sample profitable wallet for testing."""
    return {
        "address": "0x1111111111111111111111111111111111111111",
        "name": "test-whale",
        "pnl_usd": 25000.0,
        "trades_90d": 45,
        "win_rate": 0.42,
        "volume_usd": 125000.0,
        "crypto_pnl": 15000.0,
        "politics_pnl": 5000.0,
        "sports_pnl": 5000.0,
        "other_pnl": 0.0,
    }


@pytest.fixture
def sample_trade():
    """Sample trade for testing."""
    return {
        "wallet_address": "0x1111111111111111111111111111111111111111",
        "market_id": "market-123",
        "market_question": "Will BTC close above $100k?",
        "outcome": "YES",
        "side": "YES",
        "shares": 100.0,
        "price": 0.50,
        "timestamp": "2026-09-20T20:00:00Z",
    }


@pytest.fixture
def mock_database():
    """Mock database with async methods."""
    db = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_val = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value="INSERT 0 1")
    db.execute_many = AsyncMock(return_value=None)
    return db
