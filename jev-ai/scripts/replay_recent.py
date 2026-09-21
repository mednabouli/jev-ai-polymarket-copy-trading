#!/usr/bin/env python3
"""CLI script to replay the last N signals for debugging."""

import asyncio
import sys

from config import get_settings
from database import Database
from event_store import EventStore
from scripts.replay_signal import replay_signal


async def replay_recent_signals(database_url: str, count: int = 5) -> None:
    """Replay the most recent N signals."""
    db = Database(database_url)
    await db.initialize()

    rows = await db.fetch_all(
        "SELECT signal_id FROM signals ORDER BY created_at DESC LIMIT :limit",
        {"limit": count},
    )

    if not rows:
        print("No signals found.")
        await db.close()
        return

    print(f"Replaying last {len(rows)} signal(s)...\n")

    for i, row in enumerate(rows, 1):
        print(f"\n{'=' * 80}")
        print(f"SIGNAL {i}/{len(rows)}")
        print(f"{'=' * 80}")
        await replay_signal(row["signal_id"], database_url)

    await db.close()


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    settings = get_settings()

    asyncio.run(replay_recent_signals(settings.database_url, count))


if __name__ == "__main__":
    main()
