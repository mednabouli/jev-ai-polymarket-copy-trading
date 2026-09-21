"""Tests for profitable-wallet filtering and persistence."""

import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from wallet_tracker import WalletTracker


@pytest.fixture
def tracker(mock_database):
    return WalletTracker(
        db=mock_database,
        mcp_polymarket_url="http://polymarket-mcp:8766",
        min_trades_90d=20,
        min_lifetime_pnl=10_000,
        min_win_rate=0.20,
    )


def test_wallet_qualifies_when_all_thresholds_met(tracker, sample_wallet):
    assert tracker._wallet_qualifies(sample_wallet) is True


def test_wallet_rejected_for_insufficient_trade_count(tracker, sample_wallet):
    sample_wallet["trades_90d"] = 19
    assert tracker._wallet_qualifies(sample_wallet) is False


def test_wallet_rejected_for_insufficient_pnl(tracker, sample_wallet):
    sample_wallet["pnl_usd"] = 9_999
    assert tracker._wallet_qualifies(sample_wallet) is False


def test_wallet_rejected_for_insufficient_win_rate(tracker, sample_wallet):
    sample_wallet["win_rate"] = 0.19
    assert tracker._wallet_qualifies(sample_wallet) is False


@pytest.mark.asyncio
async def test_store_wallet_upserts_metrics(tracker, mock_database, sample_wallet):
    await tracker._store_wallet(sample_wallet)

    mock_database.execute.assert_awaited_once()
    query, values = mock_database.execute.await_args.args
    assert "ON CONFLICT" in query
    assert values["address"] == sample_wallet["address"]
    assert values["pnl"] == 25_000.0
