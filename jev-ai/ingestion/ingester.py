"""Polymarket data ingestion service.

Fetches leaderboard, trades, and wallet metrics from Polymarket Data API.
Persists data to PostgreSQL for analysis and copy trading signals.
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import structlog

from database import Database
from ingestion.polymarket_client import PolymarketDataClient

logger = structlog.get_logger()


class PolymarketIngester:
    """Ingests data from Polymarket and persists to database."""

    def __init__(self, db: Database, client: Optional[PolymarketDataClient] = None):
        self.db = db
        self.client = client or PolymarketDataClient()
        self._processed_trade_ids: Set[str] = set()

    async def close(self) -> None:
        await self.client.close()

    async def ingest_leaderboard(
        self,
        categories: List[str] = None,
        time_periods: List[str] = None,
    ) -> int:
        """Ingest trader leaderboard across categories and time periods.

        Args:
            categories: List of categories to fetch (default: POLITICS, SPORTS, CRYPTO)
            time_periods: List of time periods (default: DAY, WEEK, MONTH)

        Returns:
            Number of unique wallets ingested
        """
        if categories is None:
            categories = ["POLITICS", "SPORTS", "CRYPTO", "OVERALL"]
        if time_periods is None:
            time_periods = ["DAY", "WEEK", "MONTH"]

        wallets_seen: Set[str] = set()

        for category in categories:
            for period in time_periods:
                try:
                    leaderboard = await self.client.get_leaderboard(
                        category=category,
                        time_period=period,
                        order_by="PNL",
                        limit=50,
                    )

                    for entry in leaderboard:
                        wallet = entry.get("proxyWallet")
                        if not wallet:
                            continue

                        wallets_seen.add(wallet)
                        await self._upsert_wallet_metrics(entry, category, period)

                except Exception as e:
                    logger.error(
                        "Failed to ingest leaderboard",
                        category=category,
                        period=period,
                        error=str(e),
                    )

        logger.info("Leaderboard ingestion complete", wallets=len(wallets_seen))
        return len(wallets_seen)

    async def _upsert_wallet_metrics(
        self,
        entry: Dict[str, Any],
        category: str,
        period: str,
    ) -> None:
        """Upsert wallet metrics into database."""
        query = """
        INSERT INTO wallet_metrics (
            wallet_address, category, time_period, rank,
            pnl_usd, volume_usd, username, profile_image,
            verified_badge, x_username, last_updated
        ) VALUES (
            :wallet, :category, :period, :rank,
            :pnl, :volume, :username, :profile_image,
            :verified, :x_username, NOW()
        )
        ON CONFLICT (wallet_address, category, time_period) DO UPDATE SET
            rank = EXCLUDED.rank,
            pnl_usd = EXCLUDED.pnl_usd,
            volume_usd = EXCLUDED.volume_usd,
            username = EXCLUDED.username,
            profile_image = EXCLUDED.profile_image,
            verified_badge = EXCLUDED.verified_badge,
            x_username = EXCLUDED.x_username,
            last_updated = NOW()
        """

        await self.db.execute(
            query,
            {
                "wallet": entry.get("proxyWallet"),
                "category": category,
                "period": period,
                "rank": int(entry.get("rank", 0)),
                "pnl": float(entry.get("pnl", 0)),
                "volume": float(entry.get("vol", 0)),
                "username": entry.get("userName"),
                "profile_image": entry.get("profileImage"),
                "verified": entry.get("verifiedBadge", False),
                "x_username": entry.get("xUsername"),
            },
        )

    async def ingest_wallet_trades(
        self,
        wallet_addresses: List[str],
        lookback_days: int = 7,
    ) -> int:
        """Ingest recent trades for specified wallets.

        Args:
            wallet_addresses: List of wallet addresses to fetch trades for
            lookback_days: Number of days to look back

        Returns:
            Number of unique trades ingested
        """
        start_time = datetime.utcnow() - timedelta(days=lookback_days)
        total_trades = 0

        for wallet in wallet_addresses:
            try:
                trades = await self.client.get_trades(
                    user=wallet,
                    start_time=start_time,
                    limit=1000,
                )

                for trade in trades:
                    trade_id = self._compute_trade_id(trade)
                    if trade_id in self._processed_trade_ids:
                        continue

                    await self._insert_trade(trade)
                    self._processed_trade_ids.add(trade_id)
                    total_trades += 1

                logger.info(
                    "Ingested wallet trades",
                    wallet=wallet[:10],
                    count=len(trades),
                )

            except Exception as e:
                logger.error(
                    "Failed to ingest trades for wallet",
                    wallet=wallet[:10],
                    error=str(e),
                )

        logger.info("Trade ingestion complete", total_trades=total_trades)
        return total_trades

    def _compute_trade_id(self, trade: Dict[str, Any]) -> str:
        """Compute unique trade ID for deduplication."""
        wallet = trade.get("proxyWallet", "")
        condition_id = trade.get("conditionId", "")
        timestamp = trade.get("timestamp", 0)
        side = trade.get("side", "")
        price = trade.get("price", 0)
        size = trade.get("size", 0)
        return f"{wallet}:{condition_id}:{timestamp}:{side}:{price}:{size}"

    async def _insert_trade(self, trade: Dict[str, Any]) -> None:
        """Insert trade into database."""
        query = """
        INSERT INTO trades (
            wallet_address, condition_id, outcome, side,
            price, size, timestamp, market_title, slug,
            event_slug, outcome_index, transaction_hash
        ) VALUES (
            :wallet, :condition_id, :outcome, :side,
            :price, :size, :timestamp, :title, :slug,
            :event_slug, :outcome_index, :tx_hash
        )
        """

        await self.db.execute(
            query,
            {
                "wallet": trade.get("proxyWallet"),
                "condition_id": trade.get("conditionId"),
                "outcome": trade.get("outcome"),
                "side": trade.get("side"),
                "price": float(trade.get("price", 0)),
                "size": float(trade.get("size", 0)),
                "timestamp": int(trade.get("timestamp", 0)),
                "title": trade.get("title"),
                "slug": trade.get("slug"),
                "event_slug": trade.get("eventSlug"),
                "outcome_index": int(trade.get("outcomeIndex", 0)),
                "tx_hash": trade.get("transactionHash"),
            },
        )

    async def ingest_closed_positions(
        self,
        wallet_addresses: List[str],
        lookback_days: int = 30,
    ) -> int:
        """Ingest closed positions for PnL calculation.

        Args:
            wallet_addresses: List of wallets to fetch
            lookback_days: Days to look back

        Returns:
            Number of positions ingested
        """
        start_time = datetime.utcnow() - timedelta(days=lookback_days)
        total_positions = 0

        for wallet in wallet_addresses:
            try:
                positions = await self.client.get_closed_positions(
                    user=wallet,
                    start_time=start_time,
                    limit=1000,
                )

                for position in positions:
                    await self._insert_closed_position(wallet, position)
                    total_positions += 1

            except Exception as e:
                logger.error(
                    "Failed to ingest closed positions",
                    wallet=wallet[:10],
                    error=str(e),
                )

        logger.info(
            "Closed positions ingestion complete",
            total=total_positions,
        )
        return total_positions

    async def _insert_closed_position(
        self,
        wallet: str,
        position: Dict[str, Any],
    ) -> None:
        """Insert closed position into database."""
        query = """
        INSERT INTO closed_positions (
            wallet_address, condition_id, outcome, side,
            total_size, avg_price, realized_pnl, fees,
            open_timestamp, close_timestamp
        ) VALUES (
            :wallet, :condition_id, :outcome, :side,
            :total_size, :avg_price, :pnl, :fees,
            :open_ts, :close_ts
        )
        """

        await self.db.execute(
            query,
            {
                "wallet": wallet,
                "condition_id": position.get("conditionId"),
                "outcome": position.get("outcome"),
                "side": position.get("side"),
                "total_size": float(position.get("totalSize", 0)),
                "avg_price": float(position.get("avgPrice", 0)),
                "pnl": float(position.get("realizedPnl", 0)),
                "fees": float(position.get("fees", 0)),
                "open_ts": int(position.get("openTimestamp", 0)),
                "close_ts": int(position.get("closeTimestamp", 0)),
            },
        )
