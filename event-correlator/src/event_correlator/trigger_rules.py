"""Configurable trigger rules for the correlation engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .state_store import CorrelationState


class TriggerRule(ABC):
    """Abstract trigger rule evaluated against correlation state."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config

    @abstractmethod
    async def evaluate(
        self,
        trade_id: str,
        triggering_source: str,
        correlation_state: CorrelationState,
    ) -> bool:
        """Return True if the trigger condition is met."""


class AllSourcesPresentRule(TriggerRule):
    """
    Case A: Fires when all configured source systems have published
    for the same trade_id within the correlation window.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(name="all_sources_present", config=config)
        self.required_sources: set[str] = set(
            config.get("required_sources", ["system_a", "system_b", "system_c"])
        )

    async def evaluate(
        self,
        trade_id: str,
        triggering_source: str,
        correlation_state: CorrelationState,
    ) -> bool:
        present_sources = set(correlation_state.events.keys())
        return self.required_sources.issubset(present_sources)


class ImmediateOnSourceRule(TriggerRule):
    """
    Case B: Fires immediately when a specific source system publishes
    an event matching a configured topic pattern (e.g., change events).
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(name="immediate_on_source", config=config)
        self.source: str = config.get("source", "system_b")
        self.topic_pattern: str = config.get("topic_pattern", "")
        self.payload_field: str | None = config.get("payload_field")
        self.payload_value: str | None = config.get("payload_value")

    async def evaluate(
        self,
        trade_id: str,
        triggering_source: str,
        correlation_state: CorrelationState,
    ) -> bool:
        if triggering_source != self.source:
            return False

        event = correlation_state.events.get(triggering_source)
        if event is None:
            return False

        if self.topic_pattern and not _topic_matches(event.topic, self.topic_pattern):
            return False

        if self.payload_field and self.payload_value:
            actual = _get_nested_value(event.payload, self.payload_field)
            if str(actual) != self.payload_value:
                return False

        return True


def _topic_matches(topic: str, pattern: str) -> bool:
    """Simple Solace wildcard matching. '>' matches any trailing levels."""
    if pattern.endswith(">"):
        prefix = pattern[:-1]
        return topic.startswith(prefix)
    if "*" in pattern:
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")
        if len(pattern_parts) != len(topic_parts):
            return False
        return all(
            pp == "*" or pp == tp
            for pp, tp in zip(pattern_parts, topic_parts, strict=True)
        )
    return topic == pattern


def _get_nested_value(data: dict[str, Any], path: str) -> Any:
    """Simple dot-notation accessor for payload fields."""
    keys = path.split(".")
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def create_trigger_rules(rules_config: list[dict[str, Any]]) -> list[TriggerRule]:
    """Factory for creating trigger rule instances from config."""
    rules: list[TriggerRule] = []
    for rule_cfg in rules_config:
        rule_type = rule_cfg.get("type")
        if rule_type == "all_sources_present":
            rules.append(AllSourcesPresentRule(rule_cfg))
        elif rule_type == "immediate_on_source":
            rules.append(ImmediateOnSourceRule(rule_cfg))
        else:
            raise ValueError(f"Unknown trigger rule type: {rule_type!r}")
    return rules
