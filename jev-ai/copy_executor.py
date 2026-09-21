"""Copy executor module."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
import httpx

from database import Database

logger = structlog.get_logger()


class CopyExecutor:
    """Executes copy trades based on followed wallet activity."""

    def __init__(self, db: Database, mcp_polymarket_url: str, position_size_usdc: float = 50.0, max_positions: int = 10, copy_sells: bool = True):
        self.db = db
        self.mcp_url = mcp_polymarket_url
        self.position_size_usdc = position_size_usdc
        self.max_positions = max_positions
        self.copy_sells = copy_sells
        self._http_client: Optional[httpx.AsyncClient] = None
        self._last_poll_time: Optional[datetime] = None

    async def initialize(self) -> None:
        self._http_client = httpx.AsyncClient(base_url=self.mcp_url, timeout=30.0)
        self._last_poll_time = datetime.utcnow() - timedelta(minutes=5)
        logger.info("CopyExecutor initialized")

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()

    def _calculate_shares(self, trade: Dict[str, Any]) -> float:
        price = trade.get("price", 0.5)
        if price <= 0 or price >= 1:
            return 0
        return round(self.position_size_usdc / price, 4)

    async def _should_copy_trade(self, trade: Dict[str, Any]) -> bool:
        exists = await self.db.fetch_one(
            "SELECT 1 FROM copy_trades WHERE market_id = :market_id AND leader_wallet = :leader_wallet AND outcome = :outcome LIMIT 1",
            {"market_id": trade.get("market_id"), "leader_wallet": trade.get("wallet_address"), "outcome": trade.get("outcome")},
        )
        if exists:
            return False
        if trade.get("side") == "SELL" and not self.copy_sells:
            return False
        return await self._get_market_liquidity(trade.get("market_id")) >= 1000

    async def _get_market_liquidity(self, market_id: str) -> float:
        if not self._http_client:
            return 0
        try:
            response = await self._http_client.post("/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_order_book", "arguments": {"market_id": market_id}}})
            response.raise_for_status()
            order_book = response.json().get("result", {}).get("content", {})
            return sum(level.get("size", 0) for level in order_book.get("yes_bids", [])[:5]) + sum(level.get("size", 0) for level in order_book.get("yes_asks", [])[:5])
        except Exception as exc:
            logger.error("Failed to get liquidity", error=str(exc))
            return 0

    async def _get_open_positions_count(self) -> int:
        result = await self.db.fetch_one("SELECT COUNT(*) AS count FROM copy_trades WHERE status = 'open'")
        return result["count"] if result else 0

    async def _fetch_recent_leader_trades(self) -> List[Dict[str, Any]]:
        if not self._http_client:
            return []
        try:
            response = await self._http_client.post("/mcp", json={"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "get_recent_trades", "arguments": {"wallet_addresses": [], "since": self._last_poll_time.isoformat() if self._last_poll_time else None}}})
            response.raise_for_status()
            trades = response.json().get("result", {}).get("content", [])
            self._last_poll_time = datetime.utcnow()
            return trades
        except Exception as exc:
            logger.error("Failed to fetch recent trades", error=str(exc))
            return []

    async def _execute_copy_trade(self, trade: Dict[str, Any]) -> None:
        market_id = trade.get("market_id")
        outcome = trade.get("outcome")
        wallet_address = trade.get("wallet_address")
        side = trade.get("side", "BUY")
        price = trade.get("price", 0.5)
        shares = self._calculate_shares(trade)
        if shares <= 0:
            return
        await self.db.execute(
            """INSERT INTO copy_trades (market_id, outcome, leader_wallet, side, price, shares, status, created_at)
               VALUES (:market_id, :outcome, :leader_wallet, :side, :price, :shares, 'open', NOW())""",
            {"market_id": market_id, "outcome": outcome, "leader_wallet": wallet_address, "side": side, "price": price, "shares": shares},
        )
        logger.info("Copy trade executed (paper)", market_id=market_id, outcome=outcome, leader_wallet=wallet_address, side=side, shares=shares)

    async def check_and_execute(self) -> int:
        """Poll followed wallets and execute copy trades (paper trading)."""
        if not self._http_client:
            return 0
        open_count = await self._get_open_positions_count()
        if open_count >= self.max_positions:
            return 0
        recent_trades = await self._fetch_recent_leader_trades()
        executed = 0
        for trade in recent_trades:
            if await self._should_copy_trade(trade):
                await self._execute_copy_trade(trade)
                executed += 1
                if open_count + executed >= self.max_positions:
                    break
        return executed
