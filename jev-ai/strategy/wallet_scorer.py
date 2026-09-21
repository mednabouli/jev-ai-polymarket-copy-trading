"""Wallet scoring module.

Computes copiability scores for wallets based on trading patterns.
Detects market makers, arbitrageurs, and high-frequency traders.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog

from database import Database

logger = structlog.get_logger()


class WalletScorer:
    """Scores wallets for copy trading suitability."""

    def __init__(self, db: Database):
        self.db = db

    async def score_wallet(self, wallet_address: str) -> Dict[str, Any]:
        """Compute comprehensive score for a wallet.

        Returns:
            Dict with scores, flags, and metrics
        """
        metrics = await self._compute_wallet_metrics(wallet_address)
        flags = self._detect_patterns(metrics)
        score = self._compute_final_score(metrics, flags)

        return {
            "wallet_address": wallet_address,
            "metrics": metrics,
            "flags": flags,
            "score": score,
            "recommendation": self._get_recommendation(score, flags),
        }

    async def _compute_wallet_metrics(self, wallet_address: str) -> Dict[str, Any]:
        """Compute trading metrics for a wallet."""
        
        trades_90d = await self._get_trade_stats(wallet_address, days=90)
        trades_30d = await self._get_trade_stats(wallet_address, days=30)
        trades_7d = await self._get_trade_stats(wallet_address, days=7)
        
        positions = await self._get_position_stats(wallet_address)
        pnl = await self._get_pnl_stats(wallet_address)
        
        return {
            "trades_90d": trades_90d,
            "trades_30d": trades_30d,
            "trades_7d": trades_7d,
            "positions": positions,
            "pnl": pnl,
        }

    async def _get_trade_stats(self, wallet: str, days: int) -> Dict[str, Any]:
        """Get trade statistics for a time window."""
        cutoff = int((datetime.utcnow() - timedelta(days=days)).timestamp())
        
        query = """
        SELECT 
            COUNT(*) AS trade_count,
            SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) AS buys,
            SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) AS sells,
            AVG(price) AS avg_price,
            AVG(size) AS avg_size,
            SUM(size) AS total_volume,
            COUNT(DISTINCT condition_id) AS unique_markets,
            COUNT(DISTINCT DATE(to_timestamp(timestamp))) AS active_days
        FROM trades
        WHERE wallet_address = :wallet
          AND timestamp >= :cutoff
        """
        
        result = await self.db.fetch_one(query, {"wallet": wallet, "cutoff": cutoff})
        
        if not result or result["trade_count"] == 0:
            return {
                "trade_count": 0,
                "buys": 0,
                "sells": 0,
                "buy_ratio": 0.5,
                "avg_price": 0,
                "avg_size": 0,
                "total_volume": 0,
                "unique_markets": 0,
                "active_days": 0,
                "trades_per_day": 0,
            }
        
        buy_ratio = result["buys"] / result["trade_count"] if result["trade_count"] > 0 else 0.5
        
        return {
            "trade_count": result["trade_count"],
            "buys": result["buys"],
            "sells": result["sells"],
            "buy_ratio": buy_ratio,
            "avg_price": float(result["avg_price"] or 0),
            "avg_size": float(result["avg_size"] or 0),
            "total_volume": float(result["total_volume"] or 0),
            "unique_markets": result["unique_markets"],
            "active_days": result["active_days"],
            "trades_per_day": result["trade_count"] / max(result["active_days"], 1),
        }

    async def _get_position_stats(self, wallet: str) -> Dict[str, Any]:
        """Get position statistics."""
        
        query = """
        SELECT 
            COUNT(*) AS total_positions,
            AVG(total_size) AS avg_size,
            AVG(avg_price) AS avg_price,
            AVG(realized_pnl) AS avg_pnl,
            SUM(realized_pnl) AS total_pnl,
            COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) AS winners,
            COUNT(CASE WHEN realized_pnl <= 0 THEN 1 END) AS losers
        FROM closed_positions
        WHERE wallet_address = :wallet
        """
        
        result = await self.db.fetch_one(query, {"wallet": wallet})
        
        if not result or result["total_positions"] == 0:
            return {
                "total_positions": 0,
                "avg_size": 0,
                "avg_price": 0,
                "avg_pnl": 0,
                "total_pnl": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0,
                "avg_hold_time_hours": 0,
            }
        
        win_rate = result["winners"] / result["total_positions"] if result["total_positions"] > 0 else 0
        
        return {
            "total_positions": result["total_positions"],
            "avg_size": float(result["avg_size"] or 0),
            "avg_price": float(result["avg_price"] or 0),
            "avg_pnl": float(result["avg_pnl"] or 0),
            "total_pnl": float(result["total_pnl"] or 0),
            "win_count": result["winners"],
            "loss_count": result["losers"],
            "win_rate": win_rate,
            "avg_hold_time_hours": 0,
        }

    async def _get_pnl_stats(self, wallet: str) -> Dict[str, Any]:
        """Get PnL statistics across timeframes."""
        
        query = """
        SELECT 
            SUM(realized_pnl) AS total_pnl,
            AVG(realized_pnl) AS avg_pnl_per_trade,
            STDDEV(realized_pnl) AS pnl_stddev,
            MAX(realized_pnl) AS max_win,
            MIN(realized_pnl) AS max_loss
        FROM closed_positions
        WHERE wallet_address = :wallet
        """
        
        result = await self.db.fetch_one(query, {"wallet": wallet})
        
        if not result:
            return {
                "total_pnl": 0,
                "avg_pnl_per_trade": 0,
                "pnl_stddev": 0,
                "max_win": 0,
                "max_loss": 0,
                "pnl_consistency_score": 0,
            }
        
        total = float(result["total_pnl"] or 0)
        avg = float(result["avg_pnl_per_trade"] or 0)
        stddev = float(result["pnl_stddev"] or 0)
        
        consistency = 0
        if stddev > 0:
            consistency = max(0, min(1, abs(avg) / stddev))
        
        return {
            "total_pnl": total,
            "avg_pnl_per_trade": avg,
            "pnl_stddev": stddev,
            "max_win": float(result["max_win"] or 0),
            "max_loss": float(result["max_loss"] or 0),
            "pnl_consistency_score": consistency,
        }

    def _detect_patterns(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Detect trading patterns (MM, arbitrage, HFT)."""
        
        trades_90d = metrics["trades_90d"]
        trades_7d = metrics["trades_7d"]
        positions = metrics["positions"]
        
        is_market_maker = self._is_likely_market_maker(trades_90d, positions)
        is_arbitrageur = self._is_likely_arbitrageur(trades_90d, positions)
        is_hft = self._is_likely_hft(trades_7d)
        is_directional = self._is_directional_trader(trades_90d, positions)
        
        return {
            "is_market_maker": is_market_maker,
            "is_arbitrageur": is_arbitrageur,
            "is_hft": is_hft,
            "is_directional": is_directional,
            "is_copiable": is_directional and not (is_market_maker or is_arbitrageur or is_hft),
        }

    def _is_likely_market_maker(self, trades: Dict[str, Any], positions: Dict[str, Any]) -> bool:
        """Detect market making patterns.
        
        MM characteristics:
        - High trade frequency
        - Balanced buy/sell ratio (~50%)
        - Low win rate (profit from spread, not direction)
        - Many small positions
        """
        if trades["trade_count"] < 100:
            return False
        
        buy_ratio = trades["buy_ratio"]
        if not (0.45 <= buy_ratio <= 0.55):
            return False
        
        if positions["win_rate"] < 0.45 or positions["win_rate"] > 0.55:
            return False
        
        if trades["trades_per_day"] < 10:
            return False
        
        return True

    def _is_likely_arbitrageur(self, trades: Dict[str, Any], positions: Dict[str, Any]) -> bool:
        """Detect arbitrage patterns.
        
        Arb characteristics:
        - Very high win rate (>85%)
        - Small average PnL per trade
        - Low variance in PnL
        - Multiple markets simultaneously
        """
        if positions["total_positions"] < 20:
            return False
        
        if positions["win_rate"] < 0.85:
            return False
        
        pnl = positions["avg_pnl"]
        if abs(pnl) > 500:
            return False
        
        return True

    def _is_likely_hft(self, trades: Dict[str, Any]) -> bool:
        """Detect high-frequency trading.
        
        HFT characteristics:
        - Very high trades per day (>50)
        - Short holding periods
        - Many unique markets
        """
        if trades["trades_per_day"] < 50:
            return False
        
        if trades["unique_markets"] > 20:
            return True
        
        return False

    def _is_directional_trader(self, trades: Dict[str, Any], positions: Dict[str, Any]) -> bool:
        """Detect directional (conviction) trading.
        
        Directional characteristics:
        - Imbalanced buy/sell (conviction one way)
        - Moderate win rate (40-70%)
        - Reasonable trade frequency
        """
        if trades["trade_count"] < 10:
            return False
        
        buy_ratio = trades["buy_ratio"]
        if 0.45 <= buy_ratio <= 0.55:
            return False
        
        win_rate = positions["win_rate"]
        if not (0.35 <= win_rate <= 0.75):
            return False
        
        return True

    def _compute_final_score(self, metrics: Dict[str, Any], flags: Dict[str, Any]) -> Dict[str, Any]:
        """Compute final copiability score (0-100)."""
        
        if not flags["is_copiable"]:
            return {
                "overall": 0,
                "breakdown": {
                    "pattern_score": 0,
                    "performance_score": 0,
                    "consistency_score": 0,
                    "activity_score": 0,
                },
                "reason": "Non-copiable pattern detected",
            }
        
        pattern_score = 100 if flags["is_directional"] else 50
        
        pnl = metrics["pnl"]
        performance_score = min(100, max(0, 50 + pnl["total_pnl"] / 1000))
        
        consistency_score = pnl["pnl_consistency_score"] * 100
        
        activity = metrics["trades_90d"]
        activity_score = min(100, activity["trade_count"] * 2)
        
        weights = {
            "pattern": 0.35,
            "performance": 0.30,
            "consistency": 0.20,
            "activity": 0.15,
        }
        
        overall = (
            pattern_score * weights["pattern"] +
            performance_score * weights["performance"] +
            consistency_score * weights["consistency"] +
            activity_score * weights["activity"]
        )
        
        return {
            "overall": round(overall, 2),
            "breakdown": {
                "pattern_score": round(pattern_score, 2),
                "performance_score": round(performance_score, 2),
                "consistency_score": round(consistency_score, 2),
                "activity_score": round(activity_score, 2),
            },
            "reason": "Directional trader with positive edge",
        }

    def _get_recommendation(self, score: Dict[str, Any], flags: Dict[str, Any]) -> str:
        """Get trading recommendation."""
        
        if not flags["is_copiable"]:
            if flags["is_market_maker"]:
                return "AVOID - Market maker (spread profits, not directional)"
            if flags["is_arbitrageur"]:
                return "AVOID - Arbitrageur (timing-dependent, not replicable)"
            if flags["is_hft"]:
                return "AVOID - High-frequency trader (latency-dependent)"
            return "AVOID - Unknown pattern"
        
        overall = score["overall"]
        
        if overall >= 80:
            return "STRONG BUY - High conviction directional trader"
        if overall >= 60:
            return "BUY - Good directional trader"
        if overall >= 40:
            return "HOLD - Moderate edge, monitor closely"
        if overall >= 20:
            return "WEAK - Low confidence, paper trade only"
        
        return "AVOID - Insufficient data or edge"
