"""Chronological walk-forward backtesting engine."""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from database import Database
from backtesting.metrics import BacktestMetrics, calculate_metrics


@dataclass(frozen=True)
class BacktestTrade:
    leader_wallet: str
    market_id: str
    outcome: str
    side: str
    signal_timestamp: int
    entry_price: float
    exit_price: float
    shares: float
    gross_pnl_usdc: float
    fees_usdc: float
    slippage_cost_usdc: float
    net_pnl_usdc: float
    status: str


@dataclass(frozen=True)
class WalkForwardResult:
    run_id: str
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    qualified_wallets: List[str]
    trades: List[BacktestTrade]
    metrics: BacktestMetrics

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
            "qualified_wallets": self.qualified_wallets,
            "trades": [asdict(trade) for trade in self.trades],
            "metrics": self.metrics.to_dict(),
        }


class BacktestEngine:
    """Runs a no-look-ahead walk-forward backtest using ingested trade history."""

    def __init__(self, db: Database, position_size_usdc: float = 50.0, fee_rate: float = 0.02, slippage_bps: float = 100.0, min_wallet_pnl: float = 0.0, min_wallet_trades: int = 10):
        self.db = db
        self.position_size_usdc = position_size_usdc
        self.fee_rate = fee_rate
        self.slippage_bps = slippage_bps
        self.min_wallet_pnl = min_wallet_pnl
        self.min_wallet_trades = min_wallet_trades

    async def run_walk_forward(self, end_at: datetime, train_days: int = 90, test_days: int = 30) -> WalkForwardResult:
        end_at = end_at.astimezone(timezone.utc) if end_at.tzinfo else end_at.replace(tzinfo=timezone.utc)
        test_end = end_at
        test_start = test_end - timedelta(days=test_days)
        train_end = test_start
        train_start = train_end - timedelta(days=train_days)
        qualified = await self._select_wallets(train_start, train_end)
        trades = await self._replay_test_window(qualified, test_start, test_end)
        metrics = calculate_metrics(
            [trade.gross_pnl_usdc for trade in trades],
            [trade.fees_usdc for trade in trades],
            [trade.slippage_cost_usdc for trade in trades],
            self.position_size_usdc * max(1, len(qualified)),
        )
        result = WalkForwardResult(str(uuid4()), train_start, train_end, test_start, test_end, qualified, trades, metrics)
        await self._persist(result)
        return result

    async def _select_wallets(self, start: datetime, end: datetime) -> List[str]:
        query = """
        SELECT wallet_address, COUNT(*) AS trade_count,
               COALESCE(SUM(realized_pnl), 0) AS realized_pnl
        FROM closed_positions
        WHERE close_timestamp >= :start_ts AND close_timestamp < :end_ts
        GROUP BY wallet_address
        HAVING COUNT(*) >= :min_trades AND COALESCE(SUM(realized_pnl), 0) >= :min_pnl
        ORDER BY realized_pnl DESC
        """
        rows = await self.db.fetch_all(query, {
            "start_ts": int(start.timestamp()),
            "end_ts": int(end.timestamp()),
            "min_trades": self.min_wallet_trades,
            "min_pnl": self.min_wallet_pnl,
        })
        return [row["wallet_address"] for row in rows]

    async def _replay_test_window(self, wallets: List[str], start: datetime, end: datetime) -> List[BacktestTrade]:
        if not wallets:
            return []
        query = """
        SELECT t.wallet_address, t.condition_id, t.outcome, t.side, t.price, t.size, t.timestamp,
               cp.realized_pnl, cp.avg_price AS exit_price
        FROM trades t
        JOIN closed_positions cp
          ON cp.wallet_address = t.wallet_address
         AND cp.condition_id = t.condition_id
         AND cp.outcome = t.outcome
        WHERE t.wallet_address = ANY(:wallets)
          AND t.timestamp >= :start_ts AND t.timestamp < :end_ts
        ORDER BY t.timestamp ASC
        """
        rows = await self.db.fetch_all(query, {"wallets": wallets, "start_ts": int(start.timestamp()), "end_ts": int(end.timestamp())})
        results: List[BacktestTrade] = []
        for row in rows:
            raw_price = float(row["price"])
            if not 0 < raw_price < 1:
                continue
            buy = row["side"] == "BUY"
            entry_price = min(0.99, raw_price * (1 + self.slippage_bps / 10000)) if buy else max(0.01, raw_price * (1 - self.slippage_bps / 10000))
            shares = self.position_size_usdc / entry_price
            exit_price = float(row.get("exit_price") or row["price"])
            gross_pnl = shares * (exit_price - entry_price) if buy else shares * (entry_price - exit_price)
            fees = (self.position_size_usdc + shares * exit_price) * self.fee_rate
            slippage_cost = abs(entry_price - raw_price) * shares
            net_pnl = gross_pnl - fees - slippage_cost
            results.append(BacktestTrade(
                leader_wallet=row["wallet_address"], market_id=row["condition_id"], outcome=row["outcome"], side=row["side"],
                signal_timestamp=int(row["timestamp"]), entry_price=entry_price, exit_price=exit_price, shares=shares,
                gross_pnl_usdc=gross_pnl, fees_usdc=fees, slippage_cost_usdc=slippage_cost, net_pnl_usdc=net_pnl, status="closed",
            ))
        return results

    async def _persist(self, result: WalkForwardResult) -> None:
        await self.db.execute(
            """
            INSERT INTO backtest_runs (run_id, train_start, train_end, test_start, test_end, qualified_wallets, metrics)
            VALUES (:run_id, :train_start, :train_end, :test_start, :test_end, CAST(:wallets AS jsonb), CAST(:metrics AS jsonb))
            """,
            {"run_id": result.run_id, "train_start": result.train_start, "train_end": result.train_end, "test_start": result.test_start, "test_end": result.test_end, "wallets": __import__("json").dumps(result.qualified_wallets), "metrics": __import__("json").dumps(result.metrics.to_dict())},
        )
        for trade in result.trades:
            await self.db.execute(
                """
                INSERT INTO backtest_trades (run_id, leader_wallet, market_id, outcome, side, signal_timestamp, entry_price, exit_price, shares, gross_pnl_usdc, fees_usdc, slippage_cost_usdc, net_pnl_usdc, status)
                VALUES (:run_id, :leader_wallet, :market_id, :outcome, :side, :signal_timestamp, :entry_price, :exit_price, :shares, :gross_pnl_usdc, :fees_usdc, :slippage_cost_usdc, :net_pnl_usdc, :status)
                """,
                {"run_id": result.run_id, **asdict(trade)},
            )
