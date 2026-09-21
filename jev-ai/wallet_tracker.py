"""
Wallet Tracker Module

Scans Polymarket for profitable wallets and maintains the followed list.
"""

import asyncio
from typing import List, Dict, Any, Optional
import structlog
import httpx

from config import settings
from database import Database

logger = structlog.get_logger()


class WalletTracker:
    """Tracks profitable Polymarket wallets for copy trading."""
    
    def __init__(
        self,
        db: Database,
        mcp_polymarket_url: str,
        min_trades_90d: int = 20,
        min_lifetime_pnl: float = 10000.0,
        min_win_rate: float = 0.20,
    ):
        self.db = db
        self.mcp_url = mcp_polymarket_url
        self.min_trades_90d = min_trades_90d
        self.min_lifetime_pnl = min_lifetime_pnl
        self.min_win_rate = min_win_rate
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP client"""
        self._http_client = httpx.AsyncClient(
            base_url=self.mcp_url,
            timeout=30.0,
        )
        logger.info("WalletTracker initialized")
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
    
    async def scan_wallets(self) -> List[Dict[str, Any]]:
        """Scan for profitable wallets using MCP server."""
        logger.info("Scanning for profitable wallets")
        
        try:
            response = await self._http_client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "get_leaderboard",
                        "arguments": {
                            "timeframe": "90d",
                            "min_pnl": self.min_lifetime_pnl,
                            "limit": 100,
                        }
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            
            wallets = data.get("result", {}).get("content", [])
            logger.info(f"Found {len(wallets)} wallets from MCP")
            
            qualified = []
            for wallet in wallets:
                if self._wallet_qualifies(wallet):
                    await self._store_wallet(wallet)
                    qualified.append(wallet)
            
            logger.info(f"Qualified {len(qualified)} wallets")
            return qualified
            
        except Exception as e:
            logger.error("Wallet scan failed", error=str(e))
            return []
    
    def _wallet_qualifies(self, wallet: Dict[str, Any]) -> bool:
        """Check if wallet meets filter criteria"""
        trades_90d = wallet.get("trades_90d", 0)
        pnl_usd = wallet.get("pnl_usd", 0)
        win_rate = wallet.get("win_rate", 0)
        
        if trades_90d < self.min_trades_90d:
            return False
        if pnl_usd < self.min_lifetime_pnl:
            return False
        if win_rate < self.min_win_rate:
            return False
        
        return True
    
    async def _store_wallet(self, wallet: Dict[str, Any]) -> None:
        """Store or update wallet in database"""
        query = """
        INSERT INTO followed_wallets (
            wallet_address, wallet_name, lifetime_pnl_usd,
            trades_90d, win_rate, total_volume_usd,
            crypto_pnl, politics_pnl, sports_pnl, other_pnl,
            last_updated
        ) VALUES (
            :address, :name, :pnl, :trades, :win_rate, :volume,
            :crypto_pnl, :politics_pnl, :sports_pnl, :other_pnl,
            NOW()
        )
        ON CONFLICT (wallet_address) DO UPDATE SET
            wallet_name = EXCLUDED.wallet_name,
            lifetime_pnl_usd = EXCLUDED.lifetime_pnl_usd,
            trades_90d = EXCLUDED.trades_90d,
            win_rate = EXCLUDED.win_rate,
            total_volume_usd = EXCLUDED.total_volume_usd,
            crypto_pnl = EXCLUDED.crypto_pnl,
            politics_pnl = EXCLUDED.politics_pnl,
            sports_pnl = EXCLUDED.sports_pnl,
            other_pnl = EXCLUDED.other_pnl,
            last_updated = NOW()
        """
        
        await self.db.execute(
            query,
            {
                "address": wallet.get("address"),
                "name": wallet.get("name", f"Whale {wallet.get('address', '')[:8]}"),
                "pnl": wallet.get("pnl_usd", 0),
                "trades": wallet.get("trades_90d", 0),
                "win_rate": wallet.get("win_rate", 0),
                "volume": wallet.get("volume_usd", 0),
                "crypto_pnl": wallet.get("crypto_pnl", 0),
                "politics_pnl": wallet.get("politics_pnl", 0),
                "sports_pnl": wallet.get("sports_pnl", 0),
                "other_pnl": wallet.get("other_pnl", 0),
            }
        )
    
    async def get_followed_wallets(self) -> List[Dict[str, Any]]:
        """Get all actively followed wallets"""
        query = """
        SELECT * FROM followed_wallets
        WHERE is_active = true
        ORDER BY lifetime_pnl_usd DESC
        """
        return await self.db.fetch_all(query)
    
    async def get_top_wallets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top N wallets by PnL"""
        query = """
        SELECT * FROM top_followed_wallets
        LIMIT :limit
        """
        return await self.db.fetch_all(query, {"limit": limit})
