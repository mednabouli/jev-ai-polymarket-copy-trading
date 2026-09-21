#!/usr/bin/env python3
"""Run a chronological walk-forward backtest from ingested data."""

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from backtesting.engine import BacktestEngine
from config import get_settings
from database import Database


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    db = Database(settings.database_url)
    await db.initialize()
    try:
        engine = BacktestEngine(
            db,
            position_size_usdc=args.position_size,
            fee_rate=args.fee_rate,
            slippage_bps=args.slippage_bps,
            min_wallet_pnl=args.min_wallet_pnl,
            min_wallet_trades=args.min_wallet_trades,
        )
        end_at = datetime.fromisoformat(args.end.replace("Z", "+00:00")) if args.end else datetime.now(timezone.utc)
        result = await engine.run_walk_forward(end_at, args.train_days, args.test_days)
        report = result.to_dict()
        print(json.dumps(report, indent=2, default=str))
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    finally:
        await db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a no-look-ahead walk-forward backtest")
    parser.add_argument("--end", help="ISO-8601 end timestamp, default now")
    parser.add_argument("--train-days", type=int, default=90)
    parser.add_argument("--test-days", type=int, default=30)
    parser.add_argument("--position-size", type=float, default=50.0)
    parser.add_argument("--fee-rate", type=float, default=0.02)
    parser.add_argument("--slippage-bps", type=float, default=100.0)
    parser.add_argument("--min-wallet-pnl", type=float, default=0.0)
    parser.add_argument("--min-wallet-trades", type=int, default=10)
    parser.add_argument("--output", help="Optional JSON report file")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
