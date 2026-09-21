"""Test suite for Polymarket ingestion."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from ingestion.polymarket_client import PolymarketDataClient
from ingestion.ingester import PolymarketIngester


class TestPolymarketDataClient:
    """Tests for PolymarketDataClient."""

    @pytest.mark.asyncio
    async def test_get_leaderboard_success(self):
        """Test successful leaderboard fetch."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=[
            {
                "rank": "1",
                "proxyWallet": "0x1234567890abcdef1234567890abcdef12345678",
                "userName": "whale_trader",
                "pnl": 50000.0,
                "vol": 500000.0,
                "verifiedBadge": True,
            }
        ])

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = PolymarketDataClient()
            leaderboard = await client.get_leaderboard(
                category="POLITICS",
                time_period="WEEK",
                limit=10,
            )

            assert len(leaderboard) == 1
            assert leaderboard[0]["userName"] == "whale_trader"
            await client.close()

    @pytest.mark.asyncio
    async def test_get_trades_with_user(self):
        """Test fetching trades for a specific user."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=[
            {
                "proxyWallet": "0x1234567890abcdef1234567890abcdef12345678",
                "conditionId": "0xabc123...",
                "outcome": "Yes",
                "side": "BUY",
                "price": 0.65,
                "size": 1000.0,
                "timestamp": 1700000000,
                "title": "Will X win?",
                "slug": "will-x-win",
            }
        ])

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = PolymarketDataClient()
            trades = await client.get_trades(
                user="0x1234567890abcdef1234567890abcdef12345678",
                limit=100,
            )

            assert len(trades) == 1
            assert trades[0]["side"] == "BUY"
            await client.close()

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty_on_error(self):
        """Test that empty list is returned on API error."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("API error"))

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            client = PolymarketDataClient()
            leaderboard = await client.get_leaderboard()

            assert leaderboard == []
            await client.close()


class TestPolymarketIngester:
    """Tests for PolymarketIngester."""

    @pytest.mark.asyncio
    async def test_compute_trade_id_deduplication(self):
        """Test trade ID computation for deduplication."""
        mock_db = AsyncMock()
        mock_client = AsyncMock()
        ingester = PolymarketIngester(db=mock_db, client=mock_client)

        trade1 = {
            "proxyWallet": "0x1234",
            "conditionId": "0xabc",
            "timestamp": 1700000000,
            "side": "BUY",
            "price": 0.5,
            "size": 100.0,
        }

        trade_id = ingester._compute_trade_id(trade1)
        assert "0x1234:0xabc:1700000000:BUY:0.5:100.0" == trade_id

        same_trade = {
            "proxyWallet": "0x1234",
            "conditionId": "0xabc",
            "timestamp": 1700000000,
            "side": "BUY",
            "price": 0.5,
            "size": 100.0,
        }

        assert ingester._compute_trade_id(same_trade) == trade_id

    @pytest.mark.asyncio
    async def test_ingest_leaderboard_upserts_metrics(self):
        """Test that leaderboard ingestion upserts wallet metrics."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        mock_client = AsyncMock()
        mock_client.get_leaderboard = AsyncMock(return_value=[
            {
                "rank": "1",
                "proxyWallet": "0x1234567890abcdef1234567890abcdef12345678",
                "userName": "trader1",
                "pnl": 10000.0,
                "vol": 100000.0,
                "verifiedBadge": True,
            }
        ])
        mock_client.close = AsyncMock()

        ingester = PolymarketIngester(db=mock_db, client=mock_client)
        count = await ingester.ingest_leaderboard(
            categories=["POLITICS"],
            time_periods=["DAY"],
        )

        assert count == 1
        assert mock_db.execute.called
        await ingester.close()
