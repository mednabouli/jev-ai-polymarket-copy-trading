#!/usr/bin/env python3
"""CLI script to list recent signals with filtering."""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional

from config import get_settings
from database import Database


async def list_signals(
    database_url: str,
    limit: int = 20,
    status: Optional[str] = None,
    wallet: Optional[str] = None,
    market: Optional[str] = None,
) -> None:
    """List recent signals with optional filters."""
    db = Database(database_url)
    await db.initialize()

    query = """
    SELECT
        signal_id,
        leader_wallet,
        market_id,
        outcome,
        side,
        signal_price,
        wallet_score,
        market_liquidity,
        status,
        decision_reason,
        created_at
    FROM signals
    WHERE 1=1
    """
    params = {}

    if status:
        query += " AND status = :status"
        params["status"] = status
    if wallet:
        query += " AND leader_wallet = :wallet"
        params["wallet"] = wallet
    if market:
        query += " AND market_id = :market"
        params["market"] = market

    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    rows = await db.fetch_all(query, params)

    if not rows:
        print("No signals found.")
        await db.close()
        return

    print("\n" + "=" * 100)
    print(f"RECENT SIGNALS (limit={limit}, status={status or 'all'})")
    print("=" * 100)

    print(
        f"{'ID':<16} {'Wallet':<12} {'Market':<16} {'Outcome':<8} {'Side':<6} "
        f"{'Price':<8} {'Score':<6} {'Liq':<10} {'Status':<10} {'Decision':<20}"
    )
    print("-" * 100)

    for row in rows:
        signal_id_short = row["signal_id"][:16]
        wallet_short = row["leader_wallet"][:12] if row["leader_wallet"] else "N/A"
        market_short = row["market_id"][:16] if row["market_id"] else "N/A"
        outcome = row["outcome"][:8]
        side = row["side"]
        price = f"{row['signal_price']:.4f}"
        score = f"{row['wallet_score']:.1f}" if row["wallet_score"] else "N/A"
        liq = f"${float(row['market_liquidity'] or 0):,.0f}"
        status = row["status"]
        decision = (row["decision_reason"] or "")[:20]

        print(
            f"{signal_id_short:<16} {wallet_short:<12} {market_short:<16} {outcome:<8} {side:<6} "
            f"{price:<8} {score:<6} {liq:<10} {status:<10} {decision:<20}"
        )

    print("=" * 100)
    print(f"Total: {len(rows)} signals\n")

    await db.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="List recent trading signals")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of signals to show")
    parser.add_argument("--status", type=str, choices=["detected", "approved", "rejected"], help="Filter by status")
    parser.add_argument("--wallet", type=str, help="Filter by wallet address")
    parser.add_argument("--market", type=str, help="Filter by market ID")

    args = parser.parse_args()

    settings = get_settings()

    asyncio.run(
        list_signals(
            settings.database_url,
            limit=args.limit,
            status=args.status,
            wallet=args.wallet,
            market=args.market,
        )
    )


if __name__ == "__main__":
    main()
