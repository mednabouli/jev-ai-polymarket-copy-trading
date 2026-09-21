"""Copy executor module with event sourcing integration."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4
import structlog
import httpx

from database import Database
from strategy.execution_simulator import ExecutionSimulator, SimulatedFill
from event_store import EventStore

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
        max_slippage_bps: int = 500,
        latency_seconds: float = 5.0,
    ):
        self.db = db
        self.mcp_url = mcp_polymarket_url
        self.position_size_usdc = position_size_usdc
        self.max_positions = max_positions
        self.copy_sells = copy_sells
        self.max_slippage_bps = max_slippage_bps
        self.latency_seconds = latency_seconds
        self._http_client: Optional[httpx.AsyncClient] = None
        self._last_poll_time: Optional[datetime] = None
        self.simulator = ExecutionSimulator(
            position_size_usdc=position_size_usdc,
            max_slippage_bps=max_slippage_bps,
            latency_seconds=latency_seconds,
        )
        self.event_store = EventStore(db)

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

    async def _simulate_and_execute(
        self,
        trade: Dict[str, Any],
        wallet_score: int,
        market_liquidity: float,
    ) -> Optional[Dict[str, Any]]:
        """Simulate execution and insert paper trade if conditions met."""

        correlation_id = str(uuid4())
        signal = {
            "leader_wallet": trade.get("wallet_address"),
            "market_id": trade.get("market_id"),
            "outcome": trade.get("outcome"),
            "side": trade.get("side", "BUY"),
            "signal_price": trade.get("price", 0.5),
            "timestamp": datetime.utcnow(),
            "wallet_score": wallet_score,
            "market_liquidity": market_liquidity,
            "metadata": trade,
        }

        await self.event_store.record_signal(signal, correlation_id)
        signal_id = self.event_store.make_idempotency_key(
            "signal",
            signal["leader_wallet"],
            signal["market_id"],
            signal["outcome"],
            signal["timestamp"],
            signal["side"],
        )

        should_execute, reason = self.simulator.should_execute_trade(
            wallet_score=wallet_score,
            market_liquidity=market_liquidity,
            signal_age_seconds=5,
        )

        await self.event_store.record_decision(signal_id, should_execute, reason, correlation_id)

        if not should_execute:
            logger.info(
                "Skipping copy trade",
                market_id=trade.get("market_id", "")[:10],
                reason=reason,
            )
            return None

        order = {
            "signal_id": signal_id,
            "market_id": trade.get("market_id"),
            "outcome": trade.get("outcome"),
            "side": trade.get("side", "BUY"),
            "requested_size": self.position_size_usdc,
            "requested_price": trade.get("price", 0.5),
            "order_type": "market",
            "metadata": {"leader_wallet": trade.get("wallet_address")},
        }
        await self.event_store.record_order(order, correlation_id)

        signal_price = trade.get("price", 0.5)
        side = trade.get("side", "BUY")

        if side == "BUY":
            fill = self.simulator.simulate_buy(
                market_id=trade.get("market_id"),
                outcome=trade.get("outcome"),
                signal_price=signal_price,
            )
        else:
            position = await self._get_open_position(
                trade.get("market_id"),
                trade.get("outcome"),
            )
            if not position:
                return None
            fill = self.simulator.simulate_sell(
                market_id=trade.get("market_id"),
                outcome=trade.get("outcome"),
                signal_price=signal_price,
                position_size=position["shares"],
            )

        if not fill.filled:
            logger.info(
                "Simulation failed",
                market_id=trade.get("market_id", "")[:10],
                reason=fill.reason,
            )
            return None

        fill_event = {
            "order_id": order.get("signal_id"),
            "fill_price": fill.fill_price,
            "fill_size": fill.fill_size,
            "fees_usdc": fill.fees_usdc,
            "slippage_bps": fill.slippage_bps,
            "metadata": {"market_id": trade.get("market_id"), "outcome": trade.get("outcome")},
        }
        await self.event_store.record_fill(fill_event, correlation_id)

        trade_record = {
            "market_id": trade.get("market_id"),
            "outcome": trade.get("outcome"),
            "leader_wallet": trade.get("wallet_address"),
            "side": side,
            "signal_price": signal_price,
            "fill_price": fill.fill_price,
            "shares": fill.fill_size,
            "slippage_bps": fill.slippage_bps,
            "fees_usdc": fill.fees_usdc,
            "status": "open" if side == "BUY" else "closed",
        }

        await self._insert_copy_trade(trade_record)

        logger.info(
            "Copy trade executed (paper)",
            market_id=trade.get("market_id", "")[:10],
            outcome=trade.get("outcome"),
            leader_wallet=trade.get("wallet_address", "")[:10],
            side=side,
            shares=fill.fill_size,
            fill_price=fill.fill_price,
            slippage_bps=fill.slippage_bps,
            fees_usdc=fill.fees_usdc,
        )

        return trade_record

    async def _get_open_position(self, market_id: str, outcome: str) -> Optional[Dict[str, Any]]:
        result = await self.db.fetch_one(
            "SELECT * FROM copy_trades WHERE market_id = :market_id AND outcome = :outcome AND status = 'open' LIMIT 1",
            {"market_id": market_id, "outcome": outcome},
        )
        return result

    async def _insert_copy_trade(self, trade_record: Dict[str, Any]) -> None:
        if trade_record["status"] == "open":
            query = """
            INSERT INTO copy_trades (
                market_id, outcome, leader_wallet, side, signal_price,
                fill_price, shares, slippage_bps, fees_usdc, status, created_at
            ) VALUES (
                :market_id, :outcome, :leader_wallet, :side, :signal_price,
                :fill_price, :shares, :slippage_bps, :fees_usdc, 'open', NOW()
            )
            """
        else:
            query = """
            UPDATE copy_trades SET
                status = 'closed',
                exit_price = :exit_price,
                exit_slippage_bps = :exit_slippage,
                exit_fees_usdc = :exit_fees,
                closed_at = NOW()
            WHERE market_id = :market_id AND outcome = :outcome AND status = 'open'
            """
            trade_record["exit_price"] = trade_record.pop("fill_price")
            trade_record["exit_slippage"] = trade_record.pop("slippage_bps")
            trade_record["exit_fees"] = trade_record.pop("fees_usdc")

        await self.db.execute(query, trade_record)

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
            wallet_score = await self._get_wallet_score(trade.get("wallet_address"))
            liquidity = await self._get_market_liquidity(trade.get("market_id"))

            if await self._simulate_and_execute(trade, wallet_score, liquidity):
                executed += 1
                if open_count + executed >= self.max_positions:
                    break

        return executed

    async def _get_wallet_score(self, wallet_address: str) -> int:
        result = await self.db.fetch_one(
            "SELECT copiability_score FROM followed_wallets WHERE wallet_address = :wallet LIMIT 1",
            {"wallet": wallet_address},
        )
        return int(result["copiability_score"]) if result else 0
