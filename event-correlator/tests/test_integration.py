"""
Integration test: validates the full CorrelationEngine + StateStore + TriggerRules
pipeline end-to-end with realistic payloads, simulating the message flow that
the CorrelatorComponent would drive.

This test does NOT require a running Solace broker or SAM instance.
It exercises the correlation pipeline independently to prove correctness.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from event_correlator.correlation_engine import CorrelationEngine
from event_correlator.state_store import create_state_store
from event_correlator.trigger_rules import create_trigger_rules


class TestFullPipelineIntegration:
    """End-to-end test of the correlation pipeline with realistic payloads."""

    @pytest.fixture
    def triggered_events(self):
        return []

    @pytest.fixture
    def engine(self, triggered_events):
        store = create_state_store({"type": "in_memory"})
        rules = create_trigger_rules([
            {"type": "all_sources_present", "required_sources": ["system_a", "system_b", "system_c"]},
            {"type": "immediate_on_source", "source": "system_b", "topic_pattern": "events/system-b-changes/>"},
        ])

        async def on_trigger(trade_id, rule_name, state):
            triggered_events.append({
                "trade_id": trade_id,
                "rule": rule_name,
                "sources": list(state.events.keys()),
            })

        return CorrelationEngine(
            state_store=store,
            trigger_rules=rules,
            ttl_seconds=3600,
            on_trigger=on_trigger,
        )

    async def test_new_note_flow_all_three_systems(self, engine, triggered_events):
        """
        Scenario: New event flows through system_a → system_c → system_b.
        Expected: Trigger fires once all three are present.
        """
        ts = datetime.now(UTC)

        # system_a publishes first
        payload_a = {
            "tradeId": "SN-2024-001",
            "system": "system_a",
            "notional": 1_000_000,
            "currency": "EUR",
            "underlying": "EUROSTOXX50",
            "maturity": "2025-12-15",
            "counterparty": "BANK_XYZ",
        }
        fired = await engine.ingest_event(
            "SN-2024-001", "system_a", payload_a,
            "events/system-a/SN-2024-001", ts,
        )
        assert fired == []
        assert len(triggered_events) == 0

        # CR publishes second
        cr_payload = {
            "tradeId": "SN-2024-001",
            "system": "system_c",
            "capitalRequirement": 45000,
            "riskWeight": 0.04,
            "regulatoryBucket": "SA-CCR",
        }
        fired = await engine.ingest_event(
            "SN-2024-001", "system_c", cr_payload,
            "events/system-c/SN-2024-001", ts,
        )
        assert fired == []
        assert len(triggered_events) == 0

        # system_b publishes last — trigger should fire
        payload_b = {
            "tradeId": "SN-2024-001",
            "system": "system_b",
            "bookingStatus": "confirmed",
            "tradeDate": "2024-03-15",
            "settlementDate": "2024-03-17",
            "pv": 998_500,
        }
        fired = await engine.ingest_event(
            "SN-2024-001", "system_b", payload_b,
            "events/system-b/SN-2024-001", ts,
        )
        assert "all_sources_present" in fired
        assert len(triggered_events) == 1
        event = triggered_events[0]
        assert event["trade_id"] == "SN-2024-001"
        assert event["rule"] == "all_sources_present"
        assert set(event["sources"]) == {"system_a", "system_c", "system_b"}

    async def test_change_event_flow_immediate_trigger(self, engine, triggered_events):
        """
        Scenario: system_b publishes a change event.
        Expected: Immediate trigger even without other sources.
        """
        ts = datetime.now(UTC)

        change_payload = {
            "tradeId": "SN-2024-002",
            "system": "system_b",
            "event_type": "change",
            "changeType": "amendment",
            "field": "settlementDate",
            "oldValue": "2024-03-17",
            "newValue": "2024-03-19",
        }
        fired = await engine.ingest_event(
            "SN-2024-002", "system_b", change_payload,
            "events/system-b-changes/SN-2024-002", ts,
        )
        assert "immediate_on_source" in fired
        assert len(triggered_events) == 1
        assert triggered_events[0]["trade_id"] == "SN-2024-002"
        assert triggered_events[0]["rule"] == "immediate_on_source"

    async def test_interleaved_trades_independent(self, engine, triggered_events):
        """
        Scenario: Two trades arrive interleaved — events from T1 and T2 mixed.
        Expected: Each trade triggers independently.
        """
        ts = datetime.now(UTC)

        # T1: system_a
        await engine.ingest_event("T1", "system_a", {"tradeId": "T1"}, "events/system-a/T1", ts)
        # T2: system_b
        await engine.ingest_event("T2", "system_b", {"tradeId": "T2"}, "events/system-b/T2", ts)
        # T1: system_c
        await engine.ingest_event("T1", "system_c", {"tradeId": "T1"}, "events/system-c/T1", ts)
        # T2: system_a
        await engine.ingest_event("T2", "system_a", {"tradeId": "T2"}, "events/system-a/T2", ts)
        # T2: system_c → should trigger T2
        await engine.ingest_event("T2", "system_c", {"tradeId": "T2"}, "events/system-c/T2", ts)

        assert len(triggered_events) == 1
        assert triggered_events[0]["trade_id"] == "T2"

        # T1: system_b → should trigger T1
        await engine.ingest_event("T1", "system_b", {"tradeId": "T1"}, "events/system-b/T1", ts)

        assert len(triggered_events) == 2
        assert triggered_events[1]["trade_id"] == "T1"

    async def test_duplicate_events_no_double_trigger(self, engine, triggered_events):
        """
        Scenario: Same events arrive twice (redelivery from broker).
        Expected: Only one trigger fires.
        """
        ts = datetime.now(UTC)

        for _ in range(2):
            await engine.ingest_event("T1", "system_a", {"tradeId": "T1"}, "events/system-a/T1", ts)
            await engine.ingest_event("T1", "system_b", {"tradeId": "T1"}, "events/system-b/T1", ts)
            await engine.ingest_event("T1", "system_c", {"tradeId": "T1"}, "events/system-c/T1", ts)

        assert len(triggered_events) == 1

    async def test_state_store_swap_redis_mock(self):
        """
        Scenario: Verify that swapping to fakeredis works identically.
        """
        try:
            import fakeredis.aioredis
        except ImportError:
            pytest.skip("fakeredis not installed")

        from event_correlator.state_store import RedisStateStore

        store = RedisStateStore(url="redis://localhost:6379", key_prefix="test:")
        # Monkey-patch with fakeredis
        store._redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

        rules = create_trigger_rules([
            {"type": "all_sources_present", "required_sources": ["system_a", "system_b", "system_c"]},
        ])
        events_triggered: list = []

        async def on_trigger(trade_id, rule_name, state):
            events_triggered.append(trade_id)

        engine = CorrelationEngine(
            state_store=store,
            trigger_rules=rules,
            ttl_seconds=3600,
            on_trigger=on_trigger,
        )

        ts = datetime.now(UTC)
        await engine.ingest_event("T1", "system_a", {"tradeId": "T1"}, "t", ts)
        await engine.ingest_event("T1", "system_b", {"tradeId": "T1"}, "t", ts)
        await engine.ingest_event("T1", "system_c", {"tradeId": "T1"}, "t", ts)

        assert events_triggered == ["T1"]

        # Verify idempotency
        await engine.ingest_event("T1", "system_c", {"tradeId": "T1"}, "t", ts)
        assert events_triggered == ["T1"]

    async def test_state_store_database_sqlite(self, tmp_path):
        """
        Scenario: Verify that the database state store (SQLite) works end-to-end.
        Uses SAM's CacheService with SQLAlchemy backend.
        """
        try:
            from solace_ai_connector.services.cache_service import CacheService  # noqa: F401
        except ImportError:
            pytest.skip("solace_ai_connector not installed (run within SAM venv)")

        from event_correlator.state_store import DatabaseStateStore

        db_path = tmp_path / "test_correlator.db"
        store = DatabaseStateStore(
            connection_string=f"sqlite:///{db_path}",
            key_prefix="test:",
        )

        rules = create_trigger_rules([
            {"type": "all_sources_present", "required_sources": ["system_a", "system_b", "system_c"]},
        ])
        events_triggered: list = []

        async def on_trigger(trade_id, rule_name, state):
            events_triggered.append(trade_id)

        engine = CorrelationEngine(
            state_store=store,
            trigger_rules=rules,
            ttl_seconds=3600,
            on_trigger=on_trigger,
        )

        ts = datetime.now(UTC)
        await engine.ingest_event("T1", "system_a", {"tradeId": "T1"}, "t", ts)
        await engine.ingest_event("T1", "system_b", {"tradeId": "T1"}, "t", ts)
        await engine.ingest_event("T1", "system_c", {"tradeId": "T1"}, "t", ts)

        assert events_triggered == ["T1"]

        # Verify idempotency
        await engine.ingest_event("T1", "system_c", {"tradeId": "T1"}, "t", ts)
        assert events_triggered == ["T1"]

        # Verify state persists (re-read)
        state = await store.get_state("T1")
        assert state is not None
        assert set(state.events.keys()) == {"system_a", "system_b", "system_c"}
