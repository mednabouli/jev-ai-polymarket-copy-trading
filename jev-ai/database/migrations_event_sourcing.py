"""Event sourcing schema migration."""

MIGRATION = """
CREATE TABLE IF NOT EXISTS event_log (
    sequence_number BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    correlation_id UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_event_log_aggregate
    ON event_log (aggregate_type, aggregate_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_event_log_correlation
    ON event_log (correlation_id, sequence_number);

CREATE TABLE IF NOT EXISTS signals (
    signal_id VARCHAR(128) PRIMARY KEY,
    leader_wallet VARCHAR(42) NOT NULL,
    market_id VARCHAR(128) NOT NULL,
    outcome VARCHAR(255) NOT NULL,
    side VARCHAR(10) NOT NULL,
    signal_price NUMERIC(12, 8) NOT NULL,
    signal_timestamp TIMESTAMPTZ,
    wallet_score NUMERIC(5, 2),
    market_liquidity NUMERIC(20, 6),
    status VARCHAR(16) NOT NULL DEFAULT 'detected',
    decision_reason TEXT,
    decided_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_signals_market_status ON signals (market_id, status);

CREATE TABLE IF NOT EXISTS paper_orders (
    order_id UUID PRIMARY KEY,
    signal_id VARCHAR(128) NOT NULL REFERENCES signals(signal_id),
    market_id VARCHAR(128) NOT NULL,
    outcome VARCHAR(255) NOT NULL,
    side VARCHAR(10) NOT NULL,
    requested_size NUMERIC(20, 8) NOT NULL,
    requested_price NUMERIC(12, 8) NOT NULL,
    order_type VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'created',
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filled_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_paper_orders_signal ON paper_orders (signal_id);

CREATE TABLE IF NOT EXISTS fills (
    fill_id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES paper_orders(order_id),
    fill_price NUMERIC(12, 8) NOT NULL,
    fill_size NUMERIC(20, 8) NOT NULL,
    fees_usdc NUMERIC(20, 8) NOT NULL DEFAULT 0,
    slippage_bps NUMERIC(12, 4) NOT NULL DEFAULT 0,
    filled_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_fills_order ON fills (order_id);

CREATE TABLE IF NOT EXISTS market_resolutions (
    market_id VARCHAR(128) PRIMARY KEY,
    resolved_outcome VARCHAR(255) NOT NULL,
    payout_per_share NUMERIC(12, 8) NOT NULL DEFAULT 0,
    resolved_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
"""
