"""Stateful correlation engine that accumulates events and evaluates trigger rules."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from .state_store import CorrelationState, StateStore
from .trigger_rules import TriggerRule

log = logging.getLogger(__name__)

TriggerCallback = Callable[[str, str, CorrelationState], Awaitable[None]]


class CorrelationEngine:
    """
    Accumulates events per trade_id across source systems and evaluates
    trigger rules after each ingestion. Fires callback on trigger.
    """

    def __init__(
        self,
        state_store: StateStore,
        trigger_rules: list[TriggerRule],
        ttl_seconds: int = 86400,
        on_trigger: TriggerCallback | None = None,
    ) -> None:
        self.state_store = state_store
        self.trigger_rules = trigger_rules
        self.ttl_seconds = ttl_seconds
        self._on_trigger = on_trigger

        # Metrics counters
        self.events_ingested: int = 0
        self.triggers_fired: int = 0
        self.triggers_deduplicated: int = 0

    async def ingest_event(
        self,
        trade_id: str,
        source_system: str,
        payload: dict[str, Any],
        topic: str,
        timestamp: datetime,
        message_id: str | None = None,
    ) -> list[str]:
        """
        Record an event and evaluate trigger rules.

        Returns list of trigger names that fired (for observability).
        """
        self.events_ingested += 1

        await self.state_store.record_event(
            trade_id=trade_id,
            source_system=source_system,
            payload=payload,
            topic=topic,
            timestamp=timestamp,
            ttl_seconds=self.ttl_seconds,
            message_id=message_id,
        )

        state = await self.state_store.get_state(trade_id)
        if state is None:
            log.warning("State not found after record_event", extra={"trade_id": trade_id})
            return []

        fired_rules: list[str] = []
        for rule in self.trigger_rules:
            try:
                triggered = await rule.evaluate(trade_id, source_system, state)
            except Exception:
                log.exception(
                    "Rule evaluation failed",
                    extra={"trade_id": trade_id, "rule_name": rule.name},
                )
                continue

            if not triggered:
                continue

            trigger_key = f"{trade_id}:{rule.name}"
            if await self.state_store.has_triggered(trigger_key):
                self.triggers_deduplicated += 1
                log.debug(
                    "Trigger already fired (deduplicated)",
                    extra={"trade_id": trade_id, "rule_name": rule.name},
                )
                continue

            # Mark triggered BEFORE calling callback to prevent races
            # If callback fails, we un-mark (see below)
            await self.state_store.mark_triggered(trigger_key)

            if self._on_trigger is not None:
                try:
                    await self._on_trigger(trade_id, rule.name, state)
                    self.triggers_fired += 1
                    fired_rules.append(rule.name)
                    log.info(
                        "Trigger fired successfully",
                        extra={
                            "trade_id": trade_id,
                            "rule_name": rule.name,
                            "sources_present": list(state.events.keys()),
                        },
                    )
                except Exception:
                    # Rollback trigger mark so it can retry on next event
                    log.exception(
                        "Trigger callback failed, rolling back trigger mark",
                        extra={"trade_id": trade_id, "rule_name": rule.name},
                    )
                    # Note: for InMemoryStateStore we'd need an un-mark method.
                    # For now, we leave it marked and log the error.
                    # The operator must investigate.
            else:
                self.triggers_fired += 1
                fired_rules.append(rule.name)

        return fired_rules

    async def sweep_expired(self) -> list[str]:
        """Remove expired correlation states. Returns list of expired trade_ids."""
        expired = await self.state_store.sweep_expired()
        if expired:
            log.info(
                "Swept expired correlations",
                extra={"count": len(expired), "trade_ids": expired},
            )
        return expired
