"""
Jev AI - Polymarket Copy Trading Orchestrator

Main entry point for the copy trading automation system.
"""

import asyncio
import signal
import logging
from typing import Optional
import structlog

from config import get_settings, Settings
from wallet_tracker import WalletTracker
from copy_executor import CopyExecutor
from telegram_handler import TelegramHandler
from database import Database
from metrics import MetricsCollector
from ingestion.ingester import PolymarketIngester
from ingestion.polymarket_client import PolymarketDataClient

# Get settings
settings: Settings = get_settings()

# Configure structured logging
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class JevAIOrchestrator:
    """Main orchestrator for copy trading automation."""
    
    def __init__(self):
        self.db: Optional[Database] = None
        self.wallet_tracker: Optional[WalletTracker] = None
        self.copy_executor: Optional[CopyExecutor] = None
        self.telegram_handler: Optional[TelegramHandler] = None
        self.metrics: Optional[MetricsCollector] = None
        self.ingester: Optional[PolymarketIngester] = None
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self) -> None:
        """Initialize all components"""
        logger.info("Initializing Jev AI Orchestrator")
        
        self.db = Database(settings.database_url)
        await self.db.initialize()
        logger.info("Database connected")
        
        self.metrics = MetricsCollector(db=self.db)
        logger.info("Metrics collector initialized")
        
        self.ingester = PolymarketIngester(db=self.db)
        logger.info("Polymarket ingester initialized")
        
        self.wallet_tracker = WalletTracker(
            db=self.db,
            mcp_polymarket_url=settings.mcp_polymarket_url,
            min_trades_90d=settings.min_trades_90d,
            min_lifetime_pnl=settings.min_lifetime_pnl,
            min_win_rate=settings.min_win_rate,
        )
        await self.wallet_tracker.initialize()
        logger.info("Wallet tracker initialized")
        
        self.copy_executor = CopyExecutor(
            db=self.db,
            mcp_polymarket_url=settings.mcp_polymarket_url,
            position_size_usdc=settings.position_size_usdc,
            max_positions=settings.max_positions,
            copy_sells=settings.copy_sells,
        )
        await self.copy_executor.initialize()
        logger.info("Copy executor initialized")
        
        self.telegram_handler = TelegramHandler(
            db=self.db,
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            mcp_telegram_url=settings.mcp_telegram_url,
        )
        await self.telegram_handler.initialize()
        logger.info("Telegram handler initialized")
        
        logger.info("All components initialized successfully")
    
    async def run(self) -> None:
        """Main orchestration loop."""
        logger.info("Starting orchestration loop")
        
        tasks = [
            asyncio.create_task(self._ingestion_loop()),
            asyncio.create_task(self._wallet_tracking_loop()),
            asyncio.create_task(self._copy_execution_loop()),
            asyncio.create_task(self._metrics_loop()),
            asyncio.create_task(self._telegram_polling_loop()),
        ]
        
        await self._shutdown_event.wait()
        
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Orchestration loop stopped")
    
    async def _ingestion_loop(self) -> None:
        """Periodically ingest data from Polymarket API."""
        logger.info("Starting ingestion loop")
        
        while not self._shutdown_event.is_set():
            try:
                await self._run_ingestion()
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Ingestion error", error=str(e))
                await asyncio.sleep(60)
    
    async def _run_ingestion(self) -> None:
        """Run one ingestion cycle."""
        wallets = await self.db.fetch_all(
            "SELECT wallet_address FROM followed_wallets WHERE is_active = true"
        )
        wallet_addresses = [w["wallet_address"] for w in wallets]
        
        if wallet_addresses:
            await self.ingester.ingest_wallet_trades(
                wallet_addresses=wallet_addresses,
                lookback_days=7,
            )
            await self.ingester.ingest_closed_positions(
                wallet_addresses=wallet_addresses,
                lookback_days=30,
            )
        
        await self.ingester.ingest_leaderboard()
    
    async def _wallet_tracking_loop(self) -> None:
        """Continuously track profitable wallets"""
        logger.info("Starting wallet tracking loop")
        
        while not self._shutdown_event.is_set():
            try:
                await self.wallet_tracker.scan_wallets()
                await asyncio.sleep(settings.poll_interval_secs)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Wallet tracking error", error=str(e))
                await asyncio.sleep(10)
    
    async def _copy_execution_loop(self) -> None:
        """Continuously check for copy trade opportunities"""
        logger.info("Starting copy execution loop")
        
        while not self._shutdown_event.is_set():
            try:
                await self.copy_executor.check_and_execute()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Copy execution error", error=str(e))
                await asyncio.sleep(10)
    
    async def _metrics_loop(self) -> None:
        """Periodically collect and report metrics"""
        logger.info("Starting metrics loop")
        
        while not self._shutdown_event.is_set():
            try:
                await self.metrics.collect()
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Metrics collection error", error=str(e))
    
    async def _telegram_polling_loop(self) -> None:
        """Poll Telegram for user commands"""
        logger.info("Starting Telegram polling loop")
        
        try:
            await self.telegram_handler.start_polling()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Telegram polling error", error=str(e))
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Initiating graceful shutdown")
        
        self._shutdown_event.set()
        
        if self.ingester:
            await self.ingester.close()
        if self.telegram_handler:
            await self.telegram_handler.close()
        if self.copy_executor:
            await self.copy_executor.close()
        if self.wallet_tracker:
            await self.wallet_tracker.close()
        if self.db:
            await self.db.close()
        
        logger.info("Shutdown complete")
    
    def request_shutdown(self) -> None:
        """Request shutdown (called from signal handlers)"""
        logger.info("Shutdown requested")
        asyncio.create_task(self.shutdown())


async def main() -> None:
    """Main entry point"""
    orchestrator = JevAIOrchestrator()
    
    loop = asyncio.get_running_loop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: orchestrator.request_shutdown()
        )
    
    try:
        await orchestrator.initialize()
        await orchestrator.run()
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        raise
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
