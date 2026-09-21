"""
Copy Executor Module

Monitors followed wallets and executes copy trades.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
import httpx

from config import settings
from database import Database

logger = structlog.get_logger()


class CopyExecutor:
    """Executes copy trades based on followed wallet activity."""
    
    def __init__(
        self,
        db: Database,
        mcp_polymarket_url: str,
        position_size_usdc: float = 50.0,
        max_positions: int = 10,
        copy_sells: bool = True,
    ):
        self.db = db
        self.mcp_url = mcp_polymarket_url
        self.position_size_usdc = position_size_usdc
        self.max_positions = max_positions
        self.copy_sells = copy_sells
        self._http_client: Optional[httpx.AsyncClient] = None
        self._last_poll_time: Optional[datetime] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP client"""
        self._http_client = httpx.AsyncClient(
            base_url=self.mcp_url,
            timeout=30.0,
        )
        logger.info("CopyExecutor initialized")
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
    
    async def check_and_execute(self) -> int:
        """Check for new trades and execute copies."""
        try:
            wallets = await self.db.fetch_all(
                "SELECT * FROM followed_wallets WHERE is_active = true"
            )
            
            if not wallets:
                return 0
            
            open_count = await self._get_open_positions_count()
            if open_count >= self.max_positions:
                return 0
            
            wallet_addresses = [w["wallet_address"] for w in wallets]
            recent_trades = await self._get_recent_trades(wallet_addresses)
            
            executed = 0
            for trade in recent_trades:
                if await self._should_copy_trade(trade):
                    success = await self._execute_copy(trade)
                    if success:
                        executed += 1
            
            return executed
            
        except Exception as e:
            logger.error("Copy execution check failed", error=str(e))
            return 0
    
    async def _get_open_positions_count(self) -> int:
        """Get count of currently open copy positions"""
        query = "SELECT COUNT(*) FROM copy_trades WHERE status = 'open'"
        result = await self.db.fetch_one(query)
        return result["count"] if result else 0
    
    async def _get_recent_trades(
        self, wallet_addresses: List[str]
    ) -> List[Dict[str, Any]]:
        """Get recent trades from followed wallets via MCP"""
        try:
            response = await self._http_client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_wallet_trades",
                        "arguments": {
                            "wallet_addresses": wallet_addresses,
                            "since": self._last_poll_time.isoformat() if self._last_poll_time else None,
                            "limit": 50,
                        }
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            
            self._last_poll_time = datetime.utcnow()
            return data.get("result", {}).get("content", [])
            
        except Exception as e:
            logger.error("Failed to get recent trades", error=str(e))
            return []
    
    async def _should_copy_trade(self, trade: Dict[str, Any]) -> bool:
        """Determine if a trade should be copied"""
        exists = await self.db.fetch_one(
            """
            SELECT 1 FROM copy_trades
            WHERE market_id = :market_id
            AND leader_wallet = :leader_wallet
            AND outcome = :outcome
            LIMIT 1
            """,
            {
                "market_id": trade.get("market_id"),
                "leader_wallet": trade.get("wallet_address"),
                "outcome": trade.get("outcome"),
            }
        )
        
        if exists:
            return False
        
        if trade.get("side") == "SELL" and not self.copy_sells:
            return False
        
        liquidity = await self._get_market_liquidity(trade.get("market_id"))
        if liquidity < 1000:
            return False
        
        return True
    
    async def _get_market_liquidity(self, market_id: str) -> float:
        """Get market liquidity via MCP"""
        try:
            response = await self._http_client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "get_order_book",
                        "arguments": {"market_id": market_id}
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            
            order_book = data.get("result", {}).get("content", {})
            yes_bid = sum(level.get("size", 0) for level in order_book.get("yes_bids", [])[:5])
            yes_ask = sum(level.get("size", 0) for level in order_book.get("yes_asks", [])[:5])
            
            return yes_bid + yes_ask
            
        except Exception as e:
            logger.error("Failed to get liquidity", error=str(e))
            return 0
    
    async def _execute_copy(self, trade: Dict[str, Any]) -> bool:
        """Execute a copy trade"""
        start_time = datetime.utcnow()
        
        try:
            shares = self._calculate_shares(trade)
            
            response = await self._http_client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "place_order",
                        "arguments": {
                            "market_id": trade.get("market_id"),
                            "outcome": trade.get("outcome"),
                            "side": trade.get("side"),
                            "shares": shares,
                            "order_type": "market",
                        }
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("result", {}).get("success"):
                return False
            
            await self._log_copy_trade(trade, shares, result, start_time)
            
            logger.info(
                "Copy trade executed",
                market=trade.get("market_id"),
                shares=shares,
            )
            
            return True
            
        except Exception as e:
            logger.error("Copy execution failed", error=str(e))
            return False
    
    def _calculate_shares(self, trade: Dict[str, Any]) -> float:
        """Calculate number of shares to purchase"""
        price = trade.get("price", 0.5)
        if price <= 0 or price >= 1:
            return 0
        
        shares = self.position_size_usdc / price
        return round(shares, 4)
    
    async def _log_copy_trade(
        self,
        trade: Dict[str, Any],
        shares: float,
        result: Dict[str, Any],
        start_time: datetime,
    ) -> None:
        """Log copy trade to database"""
        wallet = await self.db.fetch_one(
            "SELECT id FROM followed_wallets WHERE wallet_address = :address",
            {"address": trade.get("wallet_address")}
        )
        wallet_id = wallet["id"] if wallet else None
        
        query = """
        INSERT INTO copy_trades (
            wallet_id, market_id, market_question, outcome, side,
            shares_purchased, avg_price, total_cost_usd,
            leader_wallet, leader_shares, leader_avg_price,
            status, created_at
        ) VALUES (
            :wallet_id, :market_id, :question, :outcome, :side,
            :shares, :price, :cost,
            :leader, :leader_shares, :leader_price,
            'open', NOW()
        )
        RETURNING id
        """
        
        await self.db.fetch_one(
            query,
            {
                "wallet_id": wallet_id,
                "market_id": trade.get("market_id"),
                "question": trade.get("market_question"),
                "outcome": trade.get("outcome"),
                "side": trade.get("side"),
                "shares": shares,
                "price": result.get("result", {}).get("avg_price", 0),
                "cost": shares * result.get("result", {}).get("avg_price", 0),
                "leader": trade.get("wallet_address"),
                "leader_shares": trade.get("shares"),
                "leader_price": trade.get("price"),
            }
        )
