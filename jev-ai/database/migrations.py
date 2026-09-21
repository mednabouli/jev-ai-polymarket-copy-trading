"""Database schema migrations."""

MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS wallet_metrics (
        id SERIAL PRIMARY KEY,
        wallet_address VARCHAR(42) NOT NULL,
        category VARCHAR(20) NOT NULL,
        time_period VARCHAR(10) NOT NULL,
        rank INTEGER NOT NULL DEFAULT 0,
        pnl_usd DECIMAL(20, 2) NOT NULL DEFAULT 0,
        volume_usd DECIMAL(20, 2) NOT NULL DEFAULT 0,
        username VARCHAR(255),
        profile_image TEXT,
        verified_badge BOOLEAN DEFAULT FALSE,
        x_username VARCHAR(255),
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE (wallet_address, category, time_period)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS trades (
        id SERIAL PRIMARY KEY,
        wallet_address VARCHAR(42) NOT NULL,
        condition_id VARCHAR(66) NOT NULL,
        outcome VARCHAR(255) NOT NULL,
        side VARCHAR(10) NOT NULL,
        price DECIMAL(10, 6) NOT NULL,
        size DECIMAL(20, 6) NOT NULL,
        timestamp BIGINT NOT NULL,
        market_title TEXT,
        slug TEXT,
        event_slug TEXT,
        outcome_index INTEGER,
        transaction_hash VARCHAR(66),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades (wallet_address);
    CREATE INDEX IF NOT EXISTS idx_trades_condition ON trades (condition_id);
    CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades (timestamp);
    """,
    """
    CREATE TABLE IF NOT EXISTS closed_positions (
        id SERIAL PRIMARY KEY,
        wallet_address VARCHAR(42) NOT NULL,
        condition_id VARCHAR(66) NOT NULL,
        outcome VARCHAR(255) NOT NULL,
        side VARCHAR(10) NOT NULL,
        total_size DECIMAL(20, 6) NOT NULL,
        avg_price DECIMAL(10, 6) NOT NULL,
        realized_pnl DECIMAL(20, 2) NOT NULL,
        fees DECIMAL(20, 2) NOT NULL DEFAULT 0,
        open_timestamp BIGINT NOT NULL,
        close_timestamp BIGINT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_closed_positions_wallet ON closed_positions (wallet_address);
    CREATE INDEX IF NOT EXISTS idx_closed_positions_condition ON closed_positions (condition_id);
    """,
]


async def run_migrations(db):
    """Run all database migrations."""
    for i, query in enumerate(MIGRATIONS, 1):
        try:
            await db.execute(query, {})
            print(f"Migration {i}/{len(MIGRATIONS)} applied")
        except Exception as e:
            print(f"Migration {i} failed: {e}")
            raise
