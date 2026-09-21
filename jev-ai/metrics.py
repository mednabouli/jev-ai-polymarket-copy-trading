"""Prometheus metrics collector."""

from datetime import date
import structlog
from prometheus_client import Gauge, Histogram, start_http_server

from database import Database

logger = structlog.get_logger()

COPY_TRADES_PNL = Gauge("copy_trades_pnl_usd", "Current PnL from copy trades", ["type"])
FOLLOWED_WALLETS_COUNT = Gauge("followed_wallets_count", "Number of actively followed wallets")
OPEN_POSITIONS_COUNT = Gauge("open_positions_count", "Number of open copy trade positions")
COPY_LATENCY = Histogram("copy_latency_seconds", "Latency from whale trade to copy execution")
WALLET_PNL = Gauge("wallet_pnl_usd", "PnL per followed wallet", ["wallet_address"])


class MetricsCollector:
    def __init__(self):
        self.db: Database | None = None
        self._metrics_server_started = False

    async def collect(self) -> None:
        if self.db is None:
            return
        followed = await self.db.fetch_one("SELECT COUNT(*) AS count FROM followed_wallets WHERE is_active = true")
        positions = await self.db.fetch_one("SELECT COUNT(*) AS count FROM copy_trades WHERE status = 'open'")
        pnl = await self.db.fetch_one("SELECT COALESCE(SUM(realized_pnl_usd), 0) AS realized, COALESCE(SUM(unrealized_pnl_usd), 0) AS unrealized FROM copy_trades")
        FOLLOWED_WALLETS_COUNT.set(followed["count"] if followed else 0)
        OPEN_POSITIONS_COUNT.set(positions["count"] if positions else 0)
        if pnl:
            COPY_TRADES_PNL.labels(type="realized").set(pnl["realized"] or 0)
            COPY_TRADES_PNL.labels(type="unrealized").set(pnl["unrealized"] or 0)

    def start_metrics_server(self, port: int = 9091) -> None:
        if not self._metrics_server_started:
            start_http_server(port)
            self._metrics_server_started = True
