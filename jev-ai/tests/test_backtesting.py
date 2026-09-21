from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from backtesting.engine import BacktestEngine
from backtesting.metrics import calculate_metrics


def test_metrics_calculates_net_pnl_and_drawdown():
    metrics = calculate_metrics([10.0, -20.0, 30.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0], 100.0)
    assert metrics.total_trades == 3
    assert metrics.wins == 2
    assert metrics.losses == 1
    assert metrics.net_pnl_usdc == 14.0
    assert metrics.max_drawdown_usdc > 0


@pytest.mark.asyncio
async def test_walk_forward_selects_training_wallets_before_test_window():
    db = AsyncMock()
    db.fetch_all = AsyncMock(side_effect=[
        [{"wallet_address": "0xabc", "trade_count": 12, "realized_pnl": 500.0}],
        [{"wallet_address": "0xabc", "condition_id": "m1", "outcome": "Yes", "side": "BUY", "price": 0.5, "size": 100.0, "timestamp": 1700000000, "realized_pnl": 25.0, "exit_price": 0.8}],
    ])
    db.execute = AsyncMock()
    engine = BacktestEngine(db, fee_rate=0.0, slippage_bps=0.0, min_wallet_trades=10)
    result = await engine.run_walk_forward(datetime(2024, 1, 31, tzinfo=timezone.utc), train_days=90, test_days=30)
    assert result.qualified_wallets == ["0xabc"]
    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 0.5
    selection_params = db.fetch_all.call_args_list[0].args[1]
    replay_params = db.fetch_all.call_args_list[1].args[1]
    assert selection_params["end_ts"] == replay_params["start_ts"]


@pytest.mark.asyncio
async def test_walk_forward_returns_no_trades_when_no_wallet_qualified():
    db = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.execute = AsyncMock()
    engine = BacktestEngine(db)
    result = await engine.run_walk_forward(datetime(2024, 1, 31, tzinfo=timezone.utc))
    assert result.qualified_wallets == []
    assert result.trades == []
    assert result.metrics.total_trades == 0
