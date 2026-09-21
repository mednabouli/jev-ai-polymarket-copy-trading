"""Immutable event store for paper-trading auditability."""

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from database import Database


@dataclass(frozen=True)
class TradingEvent:
    """An immutable domain event stored in the event log."""

    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: Dict[str, Any]
    idempotency_key: str
    occurred_at: datetime
    correlation_id: str


class EventStore:
    """Append-only store and replay interface for paper-trading events."""

    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def make_idempotency_key(event_type: str, *parts: Any) -> str:
        raw = ":".join([event_type, *(str(part) for part in parts)])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def append(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        idempotency_key: str,
        correlation_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> bool:
        """Append an event. Returns False when the idempotency key already exists."""
        occurred_at = occurred_at or datetime.now(timezone.utc)
        correlation_id = correlation_id or str(uuid4())
        query = """
        INSERT INTO event_log (
            event_type, aggregate_type, aggregate_id, payload,
            idempotency_key, correlation_id, occurred_at
        ) VALUES (
            :event_type, :aggregate_type, :aggregate_id, CAST(:payload AS jsonb),
            :idempotency_key, :correlation_id, :occurred_at
        )
        ON CONFLICT (idempotency_key) DO NOTHING
        """
        result = await self.db.execute_returning(
            query,
            {
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "payload": json.dumps(payload, default=str),
                "idempotency_key": idempotency_key,
                "correlation_id": correlation_id,
                "occurred_at": occurred_at,
            },
        )
        return result is not None

    async def get_events(
        self,
        aggregate_type: str,
        aggregate_id: str,
    ) -> List[TradingEvent]:
        query = """
        SELECT event_type, aggregate_type, aggregate_id, payload,
               idempotency_key, correlation_id, occurred_at
        FROM event_log
        WHERE aggregate_type = :aggregate_type AND aggregate_id = :aggregate_id
        ORDER BY sequence_number ASC
        """
        rows = await self.db.fetch_all(
            query,
            {"aggregate_type": aggregate_type, "aggregate_id": aggregate_id},
        )
        return [
            TradingEvent(
                event_type=row["event_type"],
                aggregate_type=row["aggregate_type"],
                aggregate_id=row["aggregate_id"],
                payload=row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"]),
                idempotency_key=row["idempotency_key"],
                correlation_id=row["correlation_id"],
                occurred_at=row["occurred_at"],
            )
            for row in rows
        ]

    async def record_signal(
        self,
        signal: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> bool:
        signal_id = signal.get("signal_id") or self.make_idempotency_key(
            "signal", signal.get("leader_wallet"), signal.get("market_id"),
            signal.get("outcome"), signal.get("timestamp"), signal.get("side"),
        )
        payload = {**signal, "signal_id": signal_id}
        inserted = await self.append(
            "signal_detected",
            "signal",
            signal_id,
            payload,
            idempotency_key=signal_id,
            correlation_id=correlation_id,
        )
        if inserted:
            await self.db.execute(
                """
                INSERT INTO signals (
                    signal_id, leader_wallet, market_id, outcome, side, signal_price,
                    signal_timestamp, wallet_score, market_liquidity, status, metadata
                ) VALUES (
                    :signal_id, :leader_wallet, :market_id, :outcome, :side, :signal_price,
                    :signal_timestamp, :wallet_score, :market_liquidity, 'detected',
                    CAST(:metadata AS jsonb)
                ) ON CONFLICT (signal_id) DO NOTHING
                """,
                {
                    "signal_id": signal_id,
                    "leader_wallet": signal.get("leader_wallet"),
                    "market_id": signal.get("market_id"),
                    "outcome": signal.get("outcome"),
                    "side": signal.get("side"),
                    "signal_price": signal.get("signal_price"),
                    "signal_timestamp": signal.get("timestamp"),
                    "wallet_score": signal.get("wallet_score"),
                    "market_liquidity": signal.get("market_liquidity"),
                    "metadata": json.dumps(signal.get("metadata", {}), default=str),
                },
            )
        return inserted

    async def record_decision(
        self,
        signal_id: str,
        should_execute: bool,
        reason: str,
        correlation_id: Optional[str] = None,
    ) -> bool:
        payload = {"signal_id": signal_id, "should_execute": should_execute, "reason": reason}
        key = self.make_idempotency_key("decision", signal_id, should_execute, reason)
        inserted = await self.append(
            "execution_decided", "signal", signal_id, payload, key, correlation_id
        )
        if inserted:
            await self.db.execute(
                "UPDATE signals SET status = :status, decision_reason = :reason, decided_at = NOW() WHERE signal_id = :signal_id",
                {"status": "approved" if should_execute else "rejected", "reason": reason, "signal_id": signal_id},
            )
        return inserted

    async def record_order(
        self,
        order: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> bool:
        order_id = order.get("order_id") or str(uuid4())
        payload = {**order, "order_id": order_id}
        key = self.make_idempotency_key("order", order.get("signal_id"), order_id)
        inserted = await self.append("paper_order_created", "order", order_id, payload, key, correlation_id)
        if inserted:
            await self.db.execute(
                """
                INSERT INTO paper_orders (
                    order_id, signal_id, market_id, outcome, side, requested_size,
                    requested_price, order_type, status, idempotency_key, metadata
                ) VALUES (
                    :order_id, :signal_id, :market_id, :outcome, :side, :requested_size,
                    :requested_price, :order_type, 'created', :idempotency_key,
                    CAST(:metadata AS jsonb)
                ) ON CONFLICT (idempotency_key) DO NOTHING
                """,
                {
                    "order_id": order_id,
                    "signal_id": order.get("signal_id"),
                    "market_id": order.get("market_id"),
                    "outcome": order.get("outcome"),
                    "side": order.get("side"),
                    "requested_size": order.get("requested_size"),
                    "requested_price": order.get("requested_price"),
                    "order_type": order.get("order_type", "market"),
                    "idempotency_key": key,
                    "metadata": json.dumps(order.get("metadata", {}), default=str),
                },
            )
        return inserted

    async def record_fill(
        self,
        fill: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> bool:
        fill_id = fill.get("fill_id") or str(uuid4())
        payload = {**fill, "fill_id": fill_id}
        key = self.make_idempotency_key("fill", fill.get("order_id"), fill_id)
        inserted = await self.append("paper_order_filled", "fill", fill_id, payload, key, correlation_id)
        if inserted:
            await self.db.execute(
                """
                INSERT INTO fills (
                    fill_id, order_id, fill_price, fill_size, fees_usdc,
                    slippage_bps, filled_at, metadata
                ) VALUES (
                    :fill_id, :order_id, :fill_price, :fill_size, :fees_usdc,
                    :slippage_bps, NOW(), CAST(:metadata AS jsonb)
                )
                """,
                {
                    "fill_id": fill_id,
                    "order_id": fill.get("order_id"),
                    "fill_price": fill.get("fill_price"),
                    "fill_size": fill.get("fill_size"),
                    "fees_usdc": fill.get("fees_usdc"),
                    "slippage_bps": fill.get("slippage_bps"),
                    "metadata": json.dumps(fill.get("metadata", {}), default=str),
                },
            )
            await self.db.execute(
                "UPDATE paper_orders SET status = 'filled', filled_at = NOW() WHERE order_id = :order_id",
                {"order_id": fill.get("order_id")},
            )
        return inserted

    async def record_resolution(
        self,
        resolution: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> bool:
        market_id = resolution["market_id"]
        key = self.make_idempotency_key("resolution", market_id, resolution.get("outcome"))
        inserted = await self.append(
            "market_resolved", "market", market_id, resolution, key, correlation_id
        )
        if inserted:
            await self.db.execute(
                """
                INSERT INTO market_resolutions (
                    market_id, resolved_outcome, payout_per_share, resolved_at, metadata
                ) VALUES (
                    :market_id, :outcome, :payout_per_share, NOW(), CAST(:metadata AS jsonb)
                ) ON CONFLICT (market_id) DO UPDATE SET
                    resolved_outcome = EXCLUDED.resolved_outcome,
                    payout_per_share = EXCLUDED.payout_per_share,
                    resolved_at = EXCLUDED.resolved_at,
                    metadata = EXCLUDED.metadata
                """,
                {
                    "market_id": market_id,
                    "outcome": resolution.get("outcome"),
                    "payout_per_share": resolution.get("payout_per_share", 0),
                    "metadata": json.dumps(resolution.get("metadata", {}), default=str),
                },
            )
        return inserted
