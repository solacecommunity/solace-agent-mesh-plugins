"""Tests for the CorrelationEngine."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from event_correlator.correlation_engine import CorrelationEngine
from event_correlator.state_store import InMemoryStateStore
from event_correlator.trigger_rules import create_trigger_rules


@pytest.fixture
def store():
    return InMemoryStateStore()


@pytest.fixture
def rules():
    return create_trigger_rules([
        {"type": "all_sources_present", "required_sources": ["system_a", "system_b", "system_c"]},
        {"type": "immediate_on_source", "source": "system_b", "topic_pattern": "events/system-b-changes/>"},
    ])


@pytest.fixture
def trigger_callback():
    return AsyncMock()


@pytest.fixture
def engine(store, rules, trigger_callback):
    return CorrelationEngine(
        state_store=store,
        trigger_rules=rules,
        ttl_seconds=3600,
        on_trigger=trigger_callback,
    )


class TestCaseAAllThreePresent:
    async def test_triggers_when_all_three_arrive(self, engine, trigger_callback):
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {"tradeId": "T001"}, "events/system-a/T001", ts)
        await engine.ingest_event("T001", "system_b", {"tradeId": "T001"}, "events/system-b/T001", ts)
        fired = await engine.ingest_event("T001", "system_c", {"tradeId": "T001"}, "events/system-c/T001", ts)

        assert "all_sources_present" in fired
        trigger_callback.assert_called_once()
        call_args = trigger_callback.call_args
        assert call_args[0][0] == "T001"
        assert call_args[0][1] == "all_sources_present"

    async def test_order_does_not_matter(self, engine, trigger_callback):
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_c", {}, "events/system-c/T001", ts)
        await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)
        fired = await engine.ingest_event("T001", "system_b", {}, "events/system-b/T001", ts)

        assert "all_sources_present" in fired
        trigger_callback.assert_called_once()

    async def test_does_not_fire_with_only_two(self, engine, trigger_callback):
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)
        fired = await engine.ingest_event("T001", "system_b", {}, "events/system-b/T001", ts)

        assert "all_sources_present" not in fired
        trigger_callback.assert_not_called()


class TestCaseBImmediateOnSource:
    async def test_fires_immediately_on_change_source(self, engine, trigger_callback):
        ts = datetime.now(UTC)
        fired = await engine.ingest_event(
            "T001", "system_b", {"tradeId": "T001"}, "events/system-b-changes/T001", ts
        )

        assert "immediate_on_source" in fired
        trigger_callback.assert_called_once()
        assert trigger_callback.call_args[0][1] == "immediate_on_source"

    async def test_does_not_fire_on_non_change_topic(self, engine, trigger_callback):
        ts = datetime.now(UTC)
        fired = await engine.ingest_event(
            "T001", "system_b", {"tradeId": "T001"}, "events/system-b/T001", ts
        )

        assert "immediate_on_source" not in fired

    async def test_does_not_fire_on_other_source(self, engine, trigger_callback):
        ts = datetime.now(UTC)
        fired = await engine.ingest_event(
            "T001", "system_a", {"tradeId": "T001"}, "events/system-a/T001", ts
        )

        assert "immediate_on_source" not in fired


class TestIdempotency:
    async def test_same_trigger_does_not_fire_twice(self, engine, trigger_callback):
        ts = datetime.now(UTC)
        # First: all three present
        await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)
        await engine.ingest_event("T001", "system_b", {}, "events/system-b/T001", ts)
        await engine.ingest_event("T001", "system_c", {}, "events/system-c/T001", ts)

        # Second: receive another system_a event (all still present)
        fired = await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)

        assert "all_sources_present" not in fired
        # Only one trigger overall
        assert trigger_callback.call_count == 1

    async def test_different_trades_trigger_independently(self, engine, trigger_callback):
        ts = datetime.now(UTC)
        # Trade 1
        await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)
        await engine.ingest_event("T001", "system_b", {}, "events/system-b/T001", ts)
        await engine.ingest_event("T001", "system_c", {}, "events/system-c/T001", ts)

        # Trade 2
        await engine.ingest_event("T002", "system_a", {}, "events/system-a/T002", ts)
        await engine.ingest_event("T002", "system_b", {}, "events/system-b/T002", ts)
        await engine.ingest_event("T002", "system_c", {}, "events/system-c/T002", ts)

        assert trigger_callback.call_count == 2


class TestBothRulesOnSameEvent:
    async def test_change_event_completing_set_fires_both(self, engine, trigger_callback):
        """A change event from system_b that also completes the 3-source set fires both rules."""
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)
        await engine.ingest_event("T001", "system_c", {}, "events/system-c/T001", ts)

        # This change event completes the set AND matches the change pattern
        fired = await engine.ingest_event(
            "T001", "system_b", {}, "events/system-b-changes/T001", ts
        )

        assert "all_sources_present" in fired
        assert "immediate_on_source" in fired
        assert trigger_callback.call_count == 2


class TestTTLExpiry:
    async def test_sweep_removes_expired_states(self, engine, store):
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {}, "t", ts)
        # Force expire
        store._states["T001"].expires_at = time.time() - 1

        expired = await engine.sweep_expired()
        assert "T001" in expired

    async def test_sweep_does_not_remove_active(self, engine, store):
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {}, "t", ts)

        expired = await engine.sweep_expired()
        assert expired == []


class TestMetrics:
    async def test_events_ingested_counter(self, engine):
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {}, "t", ts)
        await engine.ingest_event("T001", "system_b", {}, "t", ts)
        assert engine.events_ingested == 2

    async def test_triggers_fired_counter(self, engine):
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)
        await engine.ingest_event("T001", "system_b", {}, "events/system-b/T001", ts)
        await engine.ingest_event("T001", "system_c", {}, "events/system-c/T001", ts)
        assert engine.triggers_fired == 1

    async def test_dedup_counter(self, engine):
        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)
        await engine.ingest_event("T001", "system_b", {}, "events/system-b/T001", ts)
        await engine.ingest_event("T001", "system_c", {}, "events/system-c/T001", ts)
        # Re-trigger attempt
        await engine.ingest_event("T001", "system_c", {}, "events/system-c/T001", ts)
        assert engine.triggers_deduplicated == 1


class TestCallbackFailure:
    async def test_trigger_marked_even_if_callback_fails(self, store, rules):
        """If callback raises, trigger is still marked (no infinite retry loop)."""
        failing_callback = AsyncMock(side_effect=RuntimeError("A2A timeout"))
        engine = CorrelationEngine(
            state_store=store,
            trigger_rules=rules,
            ttl_seconds=3600,
            on_trigger=failing_callback,
        )

        ts = datetime.now(UTC)
        await engine.ingest_event("T001", "system_a", {}, "events/system-a/T001", ts)
        await engine.ingest_event("T001", "system_b", {}, "events/system-b/T001", ts)
        await engine.ingest_event("T001", "system_c", {}, "events/system-c/T001", ts)

        # Callback was attempted
        failing_callback.assert_called_once()
        # Trigger IS marked (prevents infinite retry)
        assert await store.has_triggered("T001:all_sources_present")
