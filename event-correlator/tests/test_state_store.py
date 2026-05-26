"""Tests for the InMemoryStateStore."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from event_correlator.state_store import InMemoryStateStore


@pytest.fixture
def store() -> InMemoryStateStore:
    return InMemoryStateStore()


class TestRecordAndGetState:
    async def test_record_creates_state(self, store: InMemoryStateStore):
        await store.record_event(
            trade_id="T001",
            source_system="system_a",
            payload={"tradeId": "T001", "amount": 1000},
            topic="events/system-a/T001",
            timestamp=datetime.now(UTC),
            ttl_seconds=3600,
        )
        state = await store.get_state("T001")
        assert state is not None
        assert state.trade_id == "T001"
        assert "system_a" in state.events
        assert state.events["system_a"].payload["amount"] == 1000

    async def test_record_multiple_sources(self, store: InMemoryStateStore):
        ts = datetime.now(UTC)
        await store.record_event("T001", "system_a", {"tradeId": "T001"}, "events/system-a/T001", ts, 3600)
        await store.record_event("T001", "system_b", {"tradeId": "T001"}, "events/system-b/T001", ts, 3600)
        await store.record_event("T001", "system_c", {"tradeId": "T001"}, "events/system-c/T001", ts, 3600)

        state = await store.get_state("T001")
        assert state is not None
        assert set(state.events.keys()) == {"system_a", "system_b", "system_c"}

    async def test_record_overwrites_same_source(self, store: InMemoryStateStore):
        ts = datetime.now(UTC)
        await store.record_event("T001", "system_a", {"v": 1}, "t1", ts, 3600)
        await store.record_event("T001", "system_a", {"v": 2}, "t2", ts, 3600)

        state = await store.get_state("T001")
        assert state is not None
        assert state.events["system_a"].payload == {"v": 2}

    async def test_get_state_returns_none_for_missing(self, store: InMemoryStateStore):
        state = await store.get_state("NONEXISTENT")
        assert state is None


class TestTTLExpiry:
    async def test_expired_state_returns_none(self, store: InMemoryStateStore):
        await store.record_event("T001", "system_a", {}, "t", datetime.now(UTC), ttl_seconds=1)
        # Manually expire
        store._states["T001"].expires_at = time.time() - 1
        state = await store.get_state("T001")
        assert state is None

    async def test_sweep_removes_expired(self, store: InMemoryStateStore):
        await store.record_event("T001", "system_a", {}, "t", datetime.now(UTC), ttl_seconds=1)
        await store.record_event("T002", "system_a", {}, "t", datetime.now(UTC), ttl_seconds=3600)
        store._states["T001"].expires_at = time.time() - 1

        expired = await store.sweep_expired()
        assert "T001" in expired
        assert "T002" not in expired
        assert await store.get_state("T001") is None
        assert await store.get_state("T002") is not None

    async def test_sweep_cleans_triggered_keys(self, store: InMemoryStateStore):
        await store.record_event("T001", "system_a", {}, "t", datetime.now(UTC), ttl_seconds=1)
        await store.mark_triggered("T001:all_sources_present")
        store._states["T001"].expires_at = time.time() - 1

        await store.sweep_expired()
        assert not await store.has_triggered("T001:all_sources_present")


class TestIdempotency:
    async def test_has_triggered_initially_false(self, store: InMemoryStateStore):
        assert not await store.has_triggered("T001:rule_a")

    async def test_mark_triggered_makes_it_true(self, store: InMemoryStateStore):
        await store.mark_triggered("T001:rule_a")
        assert await store.has_triggered("T001:rule_a")

    async def test_different_keys_independent(self, store: InMemoryStateStore):
        await store.mark_triggered("T001:rule_a")
        assert not await store.has_triggered("T001:rule_b")
        assert not await store.has_triggered("T002:rule_a")


class TestDeleteState:
    async def test_delete_removes_state_and_triggers(self, store: InMemoryStateStore):
        await store.record_event("T001", "system_a", {}, "t", datetime.now(UTC), 3600)
        await store.mark_triggered("T001:rule_a")

        await store.delete_state("T001")
        assert await store.get_state("T001") is None
        assert not await store.has_triggered("T001:rule_a")


class TestGetAllActive:
    async def test_returns_active_trade_ids(self, store: InMemoryStateStore):
        ts = datetime.now(UTC)
        await store.record_event("T001", "system_a", {}, "t", ts, 3600)
        await store.record_event("T002", "system_b", {}, "t", ts, 3600)

        active = await store.get_all_active_trade_ids()
        assert set(active) == {"T001", "T002"}
