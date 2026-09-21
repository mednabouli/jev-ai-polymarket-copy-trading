"""Performance metrics for paper-trading backtests."""

from dataclasses import dataclass, asdict
from math import sqrt
from statistics import mean, pstdev
from typing import Iterable, List


@dataclass(frozen=True)
class BacktestMetrics:
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    gross_pnl_usdc: float
    fees_usdc: float
    slippage_cost_usdc: float
    net_pnl_usdc: float
    profit_factor: float
    max_drawdown_usdc: float
    max_drawdown_pct: float
    sharpe_ratio: float

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_metrics(pnls: Iterable[float], fees: Iterable[float], slippage_costs: Iterable[float], starting_capital: float) -> BacktestMetrics:
    pnl_values = list(pnls)
    fee_values = list(fees)
    slippage_values = list(slippage_costs)
    net_values = [pnl - fee - slippage for pnl, fee, slippage in zip(pnl_values, fee_values, slippage_values)]
    total = len(net_values)
    wins = sum(1 for value in net_values if value > 0)
    losses = sum(1 for value in net_values if value < 0)
    gross_profit = sum(value for value in net_values if value > 0)
    gross_loss = abs(sum(value for value in net_values if value < 0))
    equity = starting_capital
    peak = starting_capital
    max_drawdown = 0.0
    for value in net_values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    returns = [value / starting_capital for value in net_values] if starting_capital else []
    if len(returns) > 1 and pstdev(returns) > 0:
        sharpe = mean(returns) / pstdev(returns) * sqrt(len(returns))
    else:
        sharpe = 0.0
    return BacktestMetrics(
        total_trades=total,
        wins=wins,
        losses=losses,
        win_rate=(wins / total) if total else 0.0,
        gross_pnl_usdc=sum(pnl_values),
        fees_usdc=sum(fee_values),
        slippage_cost_usdc=sum(slippage_values),
        net_pnl_usdc=sum(net_values),
        profit_factor=(gross_profit / gross_loss) if gross_loss else (float("inf") if gross_profit else 0.0),
        max_drawdown_usdc=max_drawdown,
        max_drawdown_pct=(max_drawdown / starting_capital) if starting_capital else 0.0,
        sharpe_ratio=sharpe,
    )
