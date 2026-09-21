"""Add copiability scoring columns to followed_wallets."""

MIGRATION = """
ALTER TABLE followed_wallets 
    ADD COLUMN IF NOT EXISTS copiability_score DECIMAL(5, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS recommendation TEXT,
    ADD COLUMN IF NOT EXISTS is_market_maker BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_arbitrageur BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_hft BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_followed_wallets_score ON followed_wallets (copiability_score DESC);
"""
