"""Shared fixtures for Event Correlator tests."""

from __future__ import annotations

import pytest

from event_correlator.correlation_engine import CorrelationEngine
from event_correlator.state_store import InMemoryStateStore
from event_correlator.trigger_rules import create_trigger_rules


@pytest.fixture
def in_memory_store() -> InMemoryStateStore:
    return InMemoryStateStore()


@pytest.fixture
def default_trigger_rules():
    return create_trigger_rules([
        {"type": "all_sources_present", "required_sources": ["system_a", "system_b", "system_c"]},
        {"type": "immediate_on_source", "source": "system_b", "topic_pattern": "events/system-b-changes/>"},
    ])


@pytest.fixture
def engine(in_memory_store, default_trigger_rules):
    return CorrelationEngine(
        state_store=in_memory_store,
        trigger_rules=default_trigger_rules,
        ttl_seconds=3600,
    )
