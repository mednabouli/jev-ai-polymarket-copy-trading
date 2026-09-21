"""Tests for copy-trade decision guards and position sizing."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from copy_executor import CopyExecutor


@pytest.fixture
def executor(mock_database):
    return CopyExecutor(
        db=mock_database,
        mcp_polymarket_url="http://polymarket-mcp:8766",
        position_size_usdc=50.0,
        max_positions=10,
        copy_sells=False,
    )


def test_calculate_shares_uses_fixed_usdc_size(executor, sample_trade):
    assert executor._calculate_shares(sample_trade) == 100.0


def test_calculate_shares_rejects_invalid_price(executor, sample_trade):
    sample_trade["price"] = 0
    assert executor._calculate_shares(sample_trade) == 0


@pytest.mark.asyncio
async def test_should_not_copy_duplicate_trade(executor, mock_database, sample_trade):
    mock_database.fetch_one.return_value = {"exists": 1}

    assert await executor._should_copy_trade(sample_trade) is False


@pytest.mark.asyncio
async def test_should_not_copy_sell_when_disabled(executor, mock_database, sample_trade):
    mock_database.fetch_one.return_value = None
    sample_trade["side"] = "SELL"

    assert await executor._should_copy_trade(sample_trade) is False


@pytest.mark.asyncio
async def test_should_not_copy_illiquid_market(executor, mock_database, sample_trade):
    mock_database.fetch_one.return_value = None
    executor._get_market_liquidity = AsyncMock(return_value=999)

    assert await executor._should_copy_trade(sample_trade) is False


@pytest.mark.asyncio
async def test_should_copy_valid_liquid_trade(executor, mock_database, sample_trade):
    mock_database.fetch_one.return_value = None
    executor._get_market_liquidity = AsyncMock(return_value=2_000)

    assert await executor._should_copy_trade(sample_trade) is True
