"""Tests for trigger rules."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from event_correlator.state_store import CorrelationState, EventRecord
from event_correlator.trigger_rules import (
    AllSourcesPresentRule,
    ImmediateOnSourceRule,
    create_trigger_rules,
)


def _make_state(trade_id: str, sources: dict[str, str]) -> CorrelationState:
    """Helper: create a CorrelationState with given sources and topics."""
    events = {}
    for source, topic in sources.items():
        events[source] = EventRecord(
            source_system=source,
            payload={"tradeId": trade_id},
            topic=topic,
            timestamp=datetime.now(UTC),
        )
    return CorrelationState(trade_id=trade_id, events=events)


class TestAllSourcesPresentRule:
    @pytest.fixture
    def rule(self):
        return AllSourcesPresentRule({"required_sources": ["system_a", "system_b", "system_c"]})

    async def test_fires_when_all_present(self, rule):
        state = _make_state("T1", {
            "system_a": "events/system-a/T1",
            "system_b": "events/system-b/T1",
            "system_c": "events/system-c/T1",
        })
        assert await rule.evaluate("T1", "system_c", state) is True

    async def test_does_not_fire_with_partial(self, rule):
        state = _make_state("T1", {
            "system_a": "events/system-a/T1",
            "system_b": "events/system-b/T1",
        })
        assert await rule.evaluate("T1", "system_b", state) is False

    async def test_does_not_fire_with_empty(self, rule):
        state = CorrelationState(trade_id="T1")
        assert await rule.evaluate("T1", "system_a", state) is False

    async def test_fires_regardless_of_order(self, rule):
        # system_a last
        state = _make_state("T1", {"system_b": "t", "system_c": "t", "system_a": "t"})
        assert await rule.evaluate("T1", "system_a", state) is True

    async def test_custom_required_sources(self):
        rule = AllSourcesPresentRule({"required_sources": ["system_a", "system_b"]})
        state = _make_state("T1", {"system_a": "t", "system_b": "t"})
        assert await rule.evaluate("T1", "system_b", state) is True


class TestImmediateOnSourceRule:
    @pytest.fixture
    def rule(self):
        return ImmediateOnSourceRule({
            "source": "system_b",
            "topic_pattern": "events/system-b-changes/>",
        })

    async def test_fires_on_matching_source_and_topic(self, rule):
        state = _make_state("T1", {"system_b": "events/system-b-changes/T1"})
        assert await rule.evaluate("T1", "system_b", state) is True

    async def test_does_not_fire_on_wrong_source(self, rule):
        state = _make_state("T1", {
            "system_a": "events/system-a/T1",
            "system_b": "events/system-b-changes/T1",
        })
        assert await rule.evaluate("T1", "system_a", state) is False

    async def test_does_not_fire_on_non_change_topic(self, rule):
        state = _make_state("T1", {"system_b": "events/system-b/T1"})
        assert await rule.evaluate("T1", "system_b", state) is False

    async def test_fires_with_subtopic(self, rule):
        state = _make_state("T1", {"system_b": "events/system-b-changes/T1/amendment"})
        assert await rule.evaluate("T1", "system_b", state) is True

    async def test_payload_field_match(self):
        rule = ImmediateOnSourceRule({
            "source": "system_b",
            "topic_pattern": "",
            "payload_field": "event_type",
            "payload_value": "change",
        })
        state = CorrelationState(trade_id="T1", events={
            "system_b": EventRecord(
                source_system="system_b",
                payload={"tradeId": "T1", "event_type": "change"},
                topic="events/system-b/T1",
                timestamp=datetime.now(UTC),
            )
        })
        assert await rule.evaluate("T1", "system_b", state) is True

    async def test_payload_field_no_match(self):
        rule = ImmediateOnSourceRule({
            "source": "system_b",
            "topic_pattern": "",
            "payload_field": "event_type",
            "payload_value": "change",
        })
        state = CorrelationState(trade_id="T1", events={
            "system_b": EventRecord(
                source_system="system_b",
                payload={"tradeId": "T1", "event_type": "new"},
                topic="events/system-b/T1",
                timestamp=datetime.now(UTC),
            )
        })
        assert await rule.evaluate("T1", "system_b", state) is False


class TestCreateTriggerRules:
    def test_creates_both_rule_types(self):
        rules = create_trigger_rules([
            {"type": "all_sources_present", "required_sources": ["a", "b"]},
            {"type": "immediate_on_source", "source": "b", "topic_pattern": "x/>"},
        ])
        assert len(rules) == 2
        assert isinstance(rules[0], AllSourcesPresentRule)
        assert isinstance(rules[1], ImmediateOnSourceRule)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown trigger rule type"):
            create_trigger_rules([{"type": "nonexistent"}])
