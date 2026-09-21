"""Test suite for wallet scoring."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from strategy.wallet_scorer import WalletScorer


class TestWalletScorer:
    """Tests for WalletScorer."""

    @pytest.mark.asyncio
    async def test_detect_market_maker(self):
        """Test market maker detection."""
        mock_db = AsyncMock()
        scorer = WalletScorer(mock_db)
        
        mm_metrics = {
            "trades_90d": {
                "trade_count": 500,
                "buy_ratio": 0.50,
                "trades_per_day": 15,
            },
            "positions": {
                "win_rate": 0.50,
                "total_positions": 200,
            },
        }
        
        assert scorer._is_likely_market_maker(mm_metrics["trades_90d"], mm_metrics["positions"]) is True

    @pytest.mark.asyncio
    async def test_detect_arbitrageur(self):
        """Test arbitrageur detection."""
        mock_db = AsyncMock()
        scorer = WalletScorer(mock_db)
        
        arb_metrics = {
            "trades_90d": {
                "trade_count": 100,
                "buy_ratio": 0.50,
            },
            "positions": {
                "win_rate": 0.90,
                "avg_pnl": 50,
                "total_positions": 50,
            },
        }
        
        assert scorer._is_likely_arbitrageur(arb_metrics["trades_90d"], arb_metrics["positions"]) is True

    @pytest.mark.asyncio
    async def test_detect_hft(self):
        """Test HFT detection."""
        mock_db = AsyncMock()
        scorer = WalletScorer(mock_db)
        
        hft_metrics = {
            "trade_count": 1000,
            "buy_ratio": 0.50,
            "trades_per_day": 100,
            "unique_markets": 30,
        }
        
        assert scorer._is_likely_hft(hft_metrics) is True

    @pytest.mark.asyncio
    async def test_detect_directional_trader(self):
        """Test directional trader detection."""
        mock_db = AsyncMock()
        scorer = WalletScorer(mock_db)
        
        directional_metrics = {
            "trades_90d": {
                "trade_count": 50,
                "buy_ratio": 0.75,
                "trades_per_day": 2,
            },
            "positions": {
                "win_rate": 0.60,
                "total_positions": 30,
            },
        }
        
        assert scorer._is_directional_trader(
            directional_metrics["trades_90d"],
            directional_metrics["positions"]
        ) is True

    @pytest.mark.asyncio
    async def test_score_non_copiable_wallet(self):
        """Test scoring a non-copiable wallet (MM)."""
        mock_db = AsyncMock()
        scorer = WalletScorer(mock_db)
        
        flags = {
            "is_market_maker": True,
            "is_arbitrageur": False,
            "is_hft": False,
            "is_directional": False,
            "is_copiable": False,
        }
        
        metrics = {"trades_90d": {}, "positions": {}, "pnl": {}}
        score = scorer._compute_final_score(metrics, flags)
        
        assert score["overall"] == 0
        assert score["reason"] == "Non-copiable pattern detected"

    @pytest.mark.asyncio
    async def test_score_good_directional_wallet(self):
        """Test scoring a good directional wallet."""
        mock_db = AsyncMock()
        scorer = WalletScorer(mock_db)
        
        flags = {
            "is_market_maker": False,
            "is_arbitrageur": False,
            "is_hft": False,
            "is_directional": True,
            "is_copiable": True,
        }
        
        metrics = {
            "trades_90d": {"trade_count": 100},
            "pnl": {
                "total_pnl": 50000,
                "pnl_consistency_score": 0.8,
            },
        }
        
        score = scorer._compute_final_score(metrics, flags)
        
        assert score["overall"] > 60
        assert score["breakdown"]["pattern_score"] == 100
