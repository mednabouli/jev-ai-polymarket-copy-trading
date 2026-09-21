"""Test suite for execution simulator."""

import pytest
from strategy.execution_simulator import ExecutionSimulator, OrderType


class TestExecutionSimulator:
    """Tests for ExecutionSimulator."""

    def test_simulate_buy_with_no_order_book(self):
        """Test BUY simulation without order book."""
        sim = ExecutionSimulator(position_size_usdc=50.0)
        fill = sim.simulate_buy(
            market_id="0xabc",
            outcome="Yes",
            signal_price=0.50,
        )

        assert fill.filled is True
        assert 0.50 < fill.fill_price < 0.55
        assert fill.slippage_bps > 0
        assert fill.fees_usdc > 0

    def test_simulate_sell_with_no_order_book(self):
        """Test SELL simulation without order book."""
        sim = ExecutionSimulator(position_size_usdc=50.0)
        fill = sim.simulate_sell(
            market_id="0xabc",
            outcome="Yes",
            signal_price=0.60,
            position_size=100.0,
        )

        assert fill.filled is True
        assert 0.55 < fill.fill_price < 0.60
        assert fill.slippage_bps > 0

    def test_simulate_buy_invalid_price(self):
        """Test BUY with invalid price."""
        sim = ExecutionSimulator()
        fill = sim.simulate_buy(
            market_id="0xabc",
            outcome="Yes",
            signal_price=1.50,
        )

        assert fill.filled is False
        assert "Invalid price" in fill.reason

    def test_calculate_expected_pnl_profitable(self):
        """Test PnL calculation for profitable trade."""
        sim = ExecutionSimulator()
        pnl = sim.calculate_expected_pnl(
            entry_price=0.40,
            exit_price=0.70,
            shares=100,
            hold_fee=True,
        )

        assert pnl > 0

    def test_calculate_expected_pnl_unprofitable(self):
        """Test PnL calculation for losing trade."""
        sim = ExecutionSimulator()
        pnl = sim.calculate_expected_pnl(
            entry_price=0.60,
            exit_price=0.40,
            shares=100,
            hold_fee=True,
        )

        assert pnl < 0

    def test_should_execute_high_score_good_liquidity(self):
        """Test execution decision with good conditions."""
        sim = ExecutionSimulator()
        should_execute, reason = sim.should_execute_trade(
            wallet_score=85,
            market_liquidity=2000,
            signal_age_seconds=2,
        )

        assert should_execute is True
        assert "Strong signal" in reason

    def test_should_execute_low_score(self):
        """Test execution decision with low wallet score."""
        sim = ExecutionSimulator()
        should_execute, reason = sim.should_execute_trade(
            wallet_score=20,
            market_liquidity=5000,
            signal_age_seconds=1,
        )

        assert should_execute is False
        assert "below threshold" in reason

    def test_should_execute_low_liquidity(self):
        """Test execution decision with low liquidity."""
        sim = ExecutionSimulator()
        should_execute, reason = sim.should_execute_trade(
            wallet_score=70,
            market_liquidity=50,
            signal_age_seconds=1,
        )

        assert should_execute is False
        assert "below minimum" in reason

    def test_should_execute_stale_signal(self):
        """Test execution decision with stale signal."""
        sim = ExecutionSimulator(latency_seconds=5.0)
        should_execute, reason = sim.should_execute_trade(
            wallet_score=70,
            market_liquidity=2000,
            signal_age_seconds=30,
        )

        assert should_execute is False
        assert "exceeds latency" in reason
