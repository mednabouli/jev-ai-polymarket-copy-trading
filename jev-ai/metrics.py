"""
Metrics Collector Module

Collects and exposes Prometheus metrics for monitoring.
"""

import asyncio
from datetime import datetime, date
import structlog
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from config import settings
from database import Database

logger = structlog.get_logger()

# Prometheus metrics
COPY_TRADES_PNL = Gauge(
    "copy_trades_pnl_usd",
    "Current PnL from copy trades",
    ["type"]
)

FOLLOWED_WALLETS_COUNT = Gauge(
    "followed_wallets_count",
    "Number of actively followed wallets"
)

OPEN_POSITIONS_COUNT = Gauge(
    "open_positions_count",
    "Number of open copy trade positions"
)

COPY_LATENCY = Histogram(
    "copy_latency_seconds",
    "Latency from whale trade to copy execution",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

WALLET_PNL = Gauge(
    "wallet_pnl_usd",
    "PnL per followed wallet",
    ["wallet_address"]
)


class MetricsCollector:
    """Collects and reports metrics"""
    
    def __init__(self):
        self.db: Database = None
        self._metrics_server_started = False
    
    async def collect(self) -> None:
        """Collect metrics from database"""
        if not self.db:
            from database import get_database
            self.db = get_database()
        
        try:
            followed = await self.db.fetch_one(
                "SELECT COUNT(*) as count FROM followed_wallets WHERE is_active = true"
            )
            FOLLOWED_WALLETS_COUNT.set(followed["count"] if followed else 0)
            
            open_positions = await self.db.fetch_one(
                "SELECT COUNT(*) as count FROM copy_trades WHERE status = 'open'"
            )
            OPEN_POSITIONS_COUNT.set(open_positions["count"] if open_positions else 0)
            
            pnl = await self.db.fetch_one(
                "SELECT COALESCE(SUM(realized_pnl_usd), 0) as realized, COALESCE(SUM(unrealized_pnl_usd), 0) as unrealized FROM copy_trades"
            )
            if pnl:
                COPY_TRADES_PNL.labels(type="realized").set(pnl["realized"] or 0)
                COPY_TRADES_PNL.labels(type="unrealized").set(pnl["unrealized"] or 0)
            
            wallets = await self.db.fetch_all(
                "SELECT wallet_address, lifetime_pnl_usd FROM followed_wallets WHERE is_active = true"
            )
            for w in wallets:
                WALLET_PNL.labels(wallet_address=w["wallet_address"][:10]).set(
                    w["lifetime_pnl_usd"] or 0
                )
            
            await self._aggregate_daily_performance()
            
        except Exception as e:
            logger.error("Metrics collection failed", error=str(e))
    
    async def _aggregate_daily_performance(self) -> None:
        """Aggregate daily performance metrics"""
        today = date.today()
        
        exists = await self.db.fetch_one(
            "SELECT 1 FROM performance_metrics WHERE date = :date",
            {"date": today}
        )
        
        if exists:
            return
        
        stats = await self.db.fetch_one(
            """
            SELECT 
                COUNT(*) as total_trades,
                COUNT(*) FILTER (WHERE realized_pnl_usd > 0) as winning_trades,
                COUNT(*) FILTER (WHERE realized_pnl_usd <= 0) as losing_trades,
                COALESCE(SUM(realized_pnl_usd), 0) as daily_pnl
            FROM copy_trades
            WHERE DATE(closed_at) = :date
            """,
            {"date": today}
        )
        
        if not stats:
            return
        
        cumulative = await self.db.fetch_one(
            "SELECT COALESCE(SUM(realized_pnl_usd), 0) as total FROM copy_trades WHERE status = 'closed'"
        )
        
        await self.db.execute(
            """
            INSERT INTO performance_metrics (
                date, total_trades, winning_trades, losing_trades,
                daily_pnl_usd, cumulative_pnl_usd
            ) VALUES (
                :date, :total, :winners, :losers, :daily_pnl, :cumulative
            )
            """,
            {
                "date": today,
                "total": stats["total_trades"] or 0,
                "winners": stats["winning_trades"] or 0,
                "losers": stats["losing_trades"] or 0,
                "daily_pnl": stats["daily_pnl"] or 0,
                "cumulative": cumulative["total"] if cumulative else 0,
            }
        )
    
    def start_metrics_server(self, port: int = 9091) -> None:
        """Start Prometheus metrics HTTP server"""
        if not self._metrics_server_started:
            start_http_server(port)
            self._metrics_server_started = True
            logger.info(f"Metrics server started on port {port}")
