"""Execution simulator module.

Models slippage, fees, and latency for realistic paper trading.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class SimulatedFill:
    """Result of a simulated order execution."""
    filled: bool
    fill_price: float
    fill_size: float
    slippage_bps: float
    fees_usdc: float
    net_cost_usdc: float
    reason: str = ""


class ExecutionSimulator:
    """Simulates trade execution with realistic market impact."""

    POLYMARKET_FEE_RATE = 0.02
    MIN_LIQUIDITY_USDC = 100.0

    def __init__(
        self,
        position_size_usdc: float = 50.0,
        max_slippage_bps: int = 500,
        latency_seconds: float = 5.0,
    ):
        self.position_size_usdc = position_size_usdc
        self.max_slippage_bps = max_slippage_bps
        self.latency_seconds = latency_seconds

    def simulate_buy(
        self,
        market_id: str,
        outcome: str,
        signal_price: float,
        order_book: Optional[Dict[str, Any]] = None,
    ) -> SimulatedFill:
        """Simulate a BUY order execution.

        Args:
            market_id: Polymarket condition ID
            outcome: "Yes" or "No"
            signal_price: Price at signal time
            order_book: Current order book (optional)

        Returns:
            SimulatedFill with execution details
        """
        if signal_price <= 0 or signal_price >= 1:
            return SimulatedFill(
                filled=False,
                fill_price=0,
                fill_size=0,
                slippage_bps=0,
                fees_usdc=0,
                net_cost_usdc=0,
                reason="Invalid price",
            )

        if order_book:
            fill_price, slippage_bps = self._simulate_market_impact_buy(
                order_book, signal_price
            )
        else:
            fill_price, slippage_bps = self._estimate_fill_price_buy(signal_price)

        if slippage_bps > self.max_slippage_bps:
            return SimulatedFill(
                filled=False,
                fill_price=0,
                fill_size=0,
                slippage_bps=slippage_bps,
                fees_usdc=0,
                net_cost_usdc=0,
                reason=f"Slippage {slippage_bps}bps exceeds max {self.max_slippage_bps}bps",
            )

        shares = self.position_size_usdc / fill_price
        fees_usdc = self.position_size_usdc * self.POLYMARKET_FEE_RATE
        net_cost = self.position_size_usdc + fees_usdc

        logger.info(
            "Simulated BUY",
            market_id=market_id[:10],
            outcome=outcome,
            signal_price=signal_price,
            fill_price=fill_price,
            shares=shares,
            slippage_bps=slippage_bps,
            fees_usdc=fees_usdc,
        )

        return SimulatedFill(
            filled=True,
            fill_price=fill_price,
            fill_size=shares,
            slippage_bps=slippage_bps,
            fees_usdc=fees_usdc,
            net_cost_usdc=net_cost,
        )

    def simulate_sell(
        self,
        market_id: str,
        outcome: str,
        signal_price: float,
        position_size: float,
        order_book: Optional[Dict[str, Any]] = None,
    ) -> SimulatedFill:
        """Simulate a SELL order execution.

        Args:
            market_id: Polymarket condition ID
            outcome: "Yes" or "No"
            signal_price: Price at signal time
            position_size: Shares to sell
            order_book: Current order book (optional)

        Returns:
            SimulatedFill with execution details
        """
        if signal_price <= 0 or signal_price >= 1:
            return SimulatedFill(
                filled=False,
                fill_price=0,
                fill_size=0,
                slippage_bps=0,
                fees_usdc=0,
                net_cost_usdc=0,
                reason="Invalid price",
            )

        if order_book:
            fill_price, slippage_bps = self._simulate_market_impact_sell(
                order_book, signal_price, position_size
            )
        else:
            fill_price, slippage_bps = self._estimate_fill_price_sell(signal_price)

        if slippage_bps > self.max_slippage_bps:
            return SimulatedFill(
                filled=False,
                fill_price=0,
                fill_size=0,
                slippage_bps=slippage_bps,
                fees_usdc=0,
                net_cost_usdc=0,
                reason=f"Slippage {slippage_bps}bps exceeds max {self.max_slippage_bps}bps",
            )

        gross_proceeds = position_size * fill_price
        fees_usdc = gross_proceeds * self.POLYMARKET_FEE_RATE
        net_proceeds = gross_proceeds - fees_usdc

        logger.info(
            "Simulated SELL",
            market_id=market_id[:10],
            outcome=outcome,
            signal_price=signal_price,
            fill_price=fill_price,
            shares=position_size,
            slippage_bps=slippage_bps,
            fees_usdc=fees_usdc,
            net_proceeds=net_proceeds,
        )

        return SimulatedFill(
            filled=True,
            fill_price=fill_price,
            fill_size=position_size,
            slippage_bps=slippage_bps,
            fees_usdc=fees_usdc,
            net_cost_usdc=-net_proceeds,
        )

    def _simulate_market_impact_buy(
        self,
        order_book: Dict[str, Any],
        signal_price: float,
    ) -> Tuple[float, float]:
        """Calculate fill price and slippage from order book (BUY)."""
        asks = order_book.get("yes_asks", [])
        if not asks:
            return signal_price * 1.05, 500

        remaining_size = self.position_size_usdc / signal_price
        total_cost = 0.0
        filled_size = 0.0

        for ask in sorted(asks, key=lambda x: x.get("price", 1)):
            ask_price = ask.get("price", 1)
            ask_size = ask.get("size", 0)

            if remaining_size <= 0:
                break

            fill_size = min(remaining_size, ask_size)
            total_cost += fill_size * ask_price
            filled_size += fill_size
            remaining_size -= fill_size

        if filled_size == 0:
            return signal_price * 1.10, 1000

        avg_fill_price = total_cost / filled_size
        slippage_bps = ((avg_fill_price - signal_price) / signal_price) * 10000

        return avg_fill_price, slippage_bps

    def _simulate_market_impact_sell(
        self,
        order_book: Dict[str, Any],
        signal_price: float,
        position_size: float,
    ) -> Tuple[float, float]:
        """Calculate fill price and slippage from order book (SELL)."""
        bids = order_book.get("yes_bids", [])
        if not bids:
            return signal_price * 0.95, 500

        remaining_size = position_size
        total_proceeds = 0.0
        filled_size = 0.0

        for bid in sorted(bids, key=lambda x: x.get("price", 0), reverse=True):
            bid_price = bid.get("price", 0)
            bid_size = bid.get("size", 0)

            if remaining_size <= 0:
                break

            fill_size = min(remaining_size, bid_size)
            total_proceeds += fill_size * bid_price
            filled_size += fill_size
            remaining_size -= fill_size

        if filled_size == 0:
            return signal_price * 0.90, 1000

        avg_fill_price = total_proceeds / filled_size
        slippage_bps = ((signal_price - avg_fill_price) / signal_price) * 10000

        return avg_fill_price, slippage_bps

    def _estimate_fill_price_buy(self, signal_price: float) -> Tuple[float, float]:
        """Estimate fill price without order book (BUY)."""
        base_slippage_bps = 50
        size_factor = min(5, self.position_size_usdc / 100)
        slippage_bps = base_slippage_bps * (1 + size_factor)

        fill_price = signal_price * (1 + slippage_bps / 10000)
        return min(fill_price, 0.99), slippage_bps

    def _estimate_fill_price_sell(self, signal_price: float) -> Tuple[float, float]:
        """Estimate fill price without order book (SELL)."""
        base_slippage_bps = 50
        size_factor = min(5, self.position_size_usdc / 100)
        slippage_bps = base_slippage_bps * (1 + size_factor)

        fill_price = signal_price * (1 - slippage_bps / 10000)
        return max(fill_price, 0.01), slippage_bps

    def calculate_expected_pnl(
        self,
        entry_price: float,
        exit_price: float,
        shares: float,
        hold_fee: bool = True,
    ) -> float:
        """Calculate expected PnL for a round-trip trade.

        Args:
            entry_price: Fill price on entry
            exit_price: Expected exit price
            shares: Number of shares
            hold_fee: Whether to include Polymarket hold fee (2%)

        Returns:
            Expected PnL in USDC
        """
        entry_cost = shares * entry_price
        entry_fees = entry_cost * self.POLYMARKET_FEE_RATE

        gross_proceeds = shares * exit_price
        exit_fees = gross_proceeds * self.POLYMARKET_FEE_RATE

        hold_fee_cost = 0
        if hold_fee:
            hold_fee_cost = shares * 0.02

        net_pnl = gross_proceeds - exit_fees - entry_cost - entry_fees - hold_fee_cost
        return net_pnl

    def should_execute_trade(
        self,
        wallet_score: int,
        market_liquidity: float,
        signal_age_seconds: float,
    ) -> Tuple[bool, str]:
        """Decision logic for whether to execute a copy trade.

        Args:
            wallet_score: Copiability score (0-100)
            market_liquidity: Order book liquidity in USDC
            signal_age_seconds: Time since signal

        Returns:
            (should_execute, reason)
        """
        if wallet_score < 40:
            return False, f"Wallet score {wallet_score} below threshold 40"

        if market_liquidity < self.MIN_LIQUIDITY_USDC:
            return False, f"Liquidity ${market_liquidity} below minimum ${self.MIN_LIQUIDITY_USDC}"

        if signal_age_seconds > self.latency_seconds * 3:
            return False, f"Signal age {signal_age_seconds}s exceeds latency budget"

        if wallet_score >= 80:
            return True, "Strong signal"
        if wallet_score >= 60 and market_liquidity >= 1000:
            return True, "Good signal with liquidity"
        if wallet_score >= 40 and market_liquidity >= 5000:
            return True, "Moderate signal with high liquidity"

        return False, "Risk/reward insufficient"
