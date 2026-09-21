#!/usr/bin/env python3
"""CLI script to replay and audit a specific signal."""

import asyncio
import json
import sys
from typing import Optional

from config import get_settings
from database import Database
from event_store import EventStore


async def replay_signal(signal_id: str, database_url: str) -> None:
    """Replay all events for a given signal and print a human-readable audit trail."""
    db = Database(database_url)
    await db.initialize()

    event_store = EventStore(db)

    signal_row = await db.fetch_one(
        "SELECT * FROM signals WHERE signal_id = :signal_id",
        {"signal_id": signal_id},
    )
    if not signal_row:
        print(f"❌ Signal {signal_id} not found in database.")
        await db.close()
        return

    events = await event_store.get_events("signal", signal_id)
    if not events:
        print(f"⚠️  No events found for signal {signal_id}.")
        await db.close()
        return

    print("\n" + "=" * 80)
    print(f"SIGNAL AUDIT: {signal_id}")
    print("=" * 80)

    print("\n📋 Signal metadata:")
    print(f"   Leader wallet : {signal_row['leader_wallet']}")
    print(f"   Market        : {signal_row['market_id']}")
    print(f"   Outcome       : {signal_row['outcome']}")
    print(f"   Side          : {signal_row['side']}")
    print(f"   Signal price  : {signal_row['signal_price']}")
    print(f"   Wallet score  : {signal_row['wallet_score']}")
    print(f"   Liquidity     : ${signal_row['market_liquidity']:.2f}")
    print(f"   Status        : {signal_row['status']}")
    if signal_row['decision_reason']:
        print(f"   Decision      : {signal_row['decision_reason']}")

    print("\n⏱️  Event timeline:")
    for i, event in enumerate(events, 1):
        occurred = event.occurred_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n   [{i}] {event.event_type} @ {occurred}")
        print(f"       Correlation ID: {event.correlation_id}")
        print(f"       Payload:")
        for key, value in event.payload.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str, indent=2).replace("\n", "\n       ")
            print(f"         • {key}: {value}")

    order = await db.fetch_one(
        "SELECT * FROM paper_orders WHERE signal_id = :signal_id",
        {"signal_id": signal_id},
    )
    if order:
        print("\n📝 Paper order:")
        print(f"   Order ID      : {order['order_id']}")
        print(f"   Requested     : {order['requested_size']} USDC @ {order['requested_price']}")
        print(f"   Type          : {order['order_type']}")
        print(f"   Status        : {order['status']}")
        if order['filled_at']:
            print(f"   Filled at     : {order['filled_at']}")

    fill = await db.fetch_one(
        "SELECT f.* FROM fills f JOIN paper_orders o ON f.order_id = o.order_id WHERE o.signal_id = :signal_id",
        {"signal_id": signal_id},
    )
    if fill:
        print("\n💰 Fill details:")
        print(f"   Fill price    : {fill['fill_price']}")
        print(f"   Fill size     : {fill['fill_size']} shares")
        print(f"   Fees          : ${fill['fees_usdc']:.4f}")
        print(f"   Slippage      : {fill['slippage_bps']:.1f} bps")

    copy_trade = await db.fetch_one(
        "SELECT * FROM copy_trades WHERE market_id = :market_id AND outcome = :outcome AND leader_wallet = :leader_wallet ORDER BY created_at DESC LIMIT 1",
        {
            "market_id": signal_row['market_id'],
            "outcome": signal_row['outcome'],
            "leader_wallet": signal_row['leader_wallet'],
        },
    )
    if copy_trade:
        print("\n📊 Copy trade projection:")
        print(f"   Status        : {copy_trade['status']}")
        if copy_trade.get('fill_price'):
            print(f"   Fill price    : {copy_trade['fill_price']}")
        if copy_trade.get('shares'):
            print(f"   Shares        : {copy_trade['shares']}")
        if copy_trade.get('exit_price'):
            pnl = (copy_trade['exit_price'] - copy_trade['fill_price']) * copy_trade['shares']
            print(f"   Exit price    : {copy_trade['exit_price']}")
            print(f"   PnL (est.)    : ${pnl:.2f}")

    print("\n" + "=" * 80)
    print("END OF AUDIT")
    print("=" * 80 + "\n")

    await db.close()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python replay_signal.py <signal_id>")
        print("\nExample:")
        print("  python replay_signal.py 5d41402abc4b2a76b9719d911017c592...")
        sys.exit(1)

    signal_id = sys.argv[1]
    settings = get_settings()

    print(f"Replaying signal: {signal_id}")
    print(f"Database: {settings.database_url}")

    asyncio.run(replay_signal(signal_id, settings.database_url))


if __name__ == "__main__":
    main()
