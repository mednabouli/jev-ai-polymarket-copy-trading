"""Tests for immutable event store."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from event_store import EventStore


@pytest.mark.asyncio
async def test_idempotency_key_is_stable():
    key_one = EventStore.make_idempotency_key("signal", "wallet", "market", "Yes", 42)
    key_two = EventStore.make_idempotency_key("signal", "wallet", "market", "Yes", 42)
    assert key_one == key_two
    assert len(key_one) == 64


@pytest.mark.asyncio
async def test_record_signal_persists_event_and_projection():
    db = AsyncMock()
    db.execute_returning = AsyncMock(return_value={"sequence_number": 1})
    db.execute = AsyncMock()
    store = EventStore(db)

    inserted = await store.record_signal({
        "leader_wallet": "0xabc",
        "market_id": "market-1",
        "outcome": "Yes",
        "side": "BUY",
        "signal_price": 0.55,
        "timestamp": datetime.now(timezone.utc),
        "wallet_score": 75,
        "market_liquidity": 2000,
    })

    assert inserted is True
    assert db.execute_returning.await_count == 1
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_duplicate_event_does_not_update_projection():
    db = AsyncMock()
    db.execute_returning = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    store = EventStore(db)

    inserted = await store.record_decision("signal-1", True, "Strong signal")

    assert inserted is False
    assert db.execute.await_count == 0


@pytest.mark.asyncio
async def test_event_replay_returns_ordered_events():
    now = datetime.now(timezone.utc)
    db = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[
        {
            "event_type": "signal_detected",
            "aggregate_type": "signal",
            "aggregate_id": "signal-1",
            "payload": {"price": 0.5},
            "idempotency_key": "key-1",
            "correlation_id": "00000000-0000-0000-0000-000000000001",
            "occurred_at": now,
        },
        {
            "event_type": "execution_decided",
            "aggregate_type": "signal",
            "aggregate_id": "signal-1",
            "payload": {"should_execute": True},
            "idempotency_key": "key-2",
            "correlation_id": "00000000-0000-0000-0000-000000000001",
            "occurred_at": now,
        },
    ])
    store = EventStore(db)

    events = await store.get_events("signal", "signal-1")

    assert [event.event_type for event in events] == ["signal_detected", "execution_decided"]
    assert events[0].payload["price"] == 0.5
