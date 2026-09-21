"""Test suite for wallet tracker module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from wallet_tracker import WalletTracker


@pytest.fixture
def mock_database():
    """Create a mock database instance."""
    db = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.execute = AsyncMock()
    return db


@pytest.fixture
def tracker(mock_database):
    """Create a WalletTracker instance with mocked dependencies."""
    return WalletTracker(
        db=mock_database,
        mcp_polymarket_url="http://localhost:8081",
    )


@pytest.fixture
def sample_wallet():
    """Sample wallet data for testing."""
    return {
        "address": "0x1111111111111111111111111111111111111111",
        "name": "test-whale",
        "pnl_usd": 25000.0,
        "trades_90d": 45,
        "win_rate": 0.65,
        "volume_usd": 150000.0,
        "crypto_pnl": 5000.0,
        "politics_pnl": 15000.0,
        "sports_pnl": 3000.0,
        "other_pnl": 2000.0,
    }


@pytest.fixture
def sample_score_result():
    """Sample scoring result for testing."""
    return {
        "wallet_address": "0x1111111111111111111111111111111111111111",
        "metrics": {},
        "flags": {
            "is_market_maker": False,
            "is_arbitrageur": False,
            "is_hft": False,
            "is_directional": True,
            "is_copiable": True,
        },
        "score": {
            "overall": 75.5,
            "breakdown": {
                "pattern_score": 100,
                "performance_score": 80,
                "consistency_score": 60,
                "activity_score": 70,
            },
        },
        "recommendation": "BUY - Good directional trader",
    }


class TestWalletTracker:
    """Tests for WalletTracker class."""

    @pytest.mark.asyncio
    async def test_wallet_qualifies_when_all_thresholds_met(self, tracker, sample_wallet):
        """Test that a wallet qualifies when all thresholds are met."""
        assert tracker._wallet_qualifies(sample_wallet) is True

    @pytest.mark.asyncio
    async def test_wallet_rejected_for_insufficient_trade_count(self, tracker, sample_wallet):
        """Test that a wallet is rejected for insufficient trade count."""
        sample_wallet["trades_90d"] = 10
        assert tracker._wallet_qualifies(sample_wallet) is False

    @pytest.mark.asyncio
    async def test_wallet_rejected_for_insufficient_pnl(self, tracker, sample_wallet):
        """Test that a wallet is rejected for insufficient PnL."""
        sample_wallet["pnl_usd"] = 5000.0
        assert tracker._wallet_qualifies(sample_wallet) is False

    @pytest.mark.asyncio
    async def test_wallet_rejected_for_insufficient_win_rate(self, tracker, sample_wallet):
        """Test that a wallet is rejected for insufficient win rate."""
        sample_wallet["win_rate"] = 0.10
        assert tracker._wallet_qualifies(sample_wallet) is False

    @pytest.mark.asyncio
    async def test_store_wallet_upserts_metrics(self, tracker, mock_database, sample_wallet, sample_score_result):
        """Test that _store_wallet upserts wallet metrics with scoring data."""
        await tracker._store_wallet(sample_wallet, sample_score_result)

        assert mock_database.execute.called
        call_args = mock_database.execute.call_args
        query = call_args[0][0]

        assert "INSERT INTO followed_wallets" in query
        assert "ON CONFLICT (wallet_address) DO UPDATE" in query
        assert "copiability_score" in query
        assert "recommendation" in query
        assert "is_market_maker" in query
