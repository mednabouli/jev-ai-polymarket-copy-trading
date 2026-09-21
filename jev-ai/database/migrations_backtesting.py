"""Walk-forward backtesting schema migration."""

MIGRATION = """
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id UUID PRIMARY KEY,
    train_start TIMESTAMPTZ NOT NULL,
    train_end TIMESTAMPTZ NOT NULL,
    test_start TIMESTAMPTZ NOT NULL,
    test_end TIMESTAMPTZ NOT NULL,
    qualified_wallets JSONB NOT NULL DEFAULT '[]'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS backtest_trades (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES backtest_runs(run_id) ON DELETE CASCADE,
    leader_wallet VARCHAR(42) NOT NULL,
    market_id VARCHAR(128) NOT NULL,
    outcome VARCHAR(255) NOT NULL,
    side VARCHAR(10) NOT NULL,
    signal_timestamp BIGINT NOT NULL,
    entry_price NUMERIC(12, 8) NOT NULL,
    exit_price NUMERIC(12, 8) NOT NULL,
    shares NUMERIC(20, 8) NOT NULL,
    gross_pnl_usdc NUMERIC(20, 8) NOT NULL,
    fees_usdc NUMERIC(20, 8) NOT NULL,
    slippage_cost_usdc NUMERIC(20, 8) NOT NULL,
    net_pnl_usdc NUMERIC(20, 8) NOT NULL,
    status VARCHAR(16) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_run ON backtest_trades(run_id);
"""
