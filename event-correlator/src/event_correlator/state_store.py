"""Pluggable state store for correlation tracking."""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EventRecord:
    source_system: str
    payload: dict[str, Any]
    topic: str
    timestamp: datetime
    message_id: str | None = None


@dataclass
class CorrelationState:
    trade_id: str
    events: dict[str, EventRecord] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0


class StateStore(ABC):
    """Abstract state store for correlation tracking."""

    @abstractmethod
    async def record_event(
        self,
        trade_id: str,
        source_system: str,
        payload: dict[str, Any],
        topic: str,
        timestamp: datetime,
        ttl_seconds: int,
        message_id: str | None = None,
    ) -> None:
        """Record an event arrival. Upserts source data and extends TTL."""

    @abstractmethod
    async def get_state(self, trade_id: str) -> CorrelationState | None:
        """Get the full correlation state for a trade_id."""

    @abstractmethod
    async def has_triggered(self, trigger_key: str) -> bool:
        """Check if a specific trigger has already fired (idempotency)."""

    @abstractmethod
    async def mark_triggered(self, trigger_key: str) -> None:
        """Mark a trigger as fired."""

    @abstractmethod
    async def sweep_expired(self) -> list[str]:
        """Remove all expired states. Returns expired trade_ids."""

    @abstractmethod
    async def delete_state(self, trade_id: str) -> None:
        """Explicitly remove state for a trade_id."""

    @abstractmethod
    async def get_all_active_trade_ids(self) -> list[str]:
        """Return all non-expired trade_ids (for metrics)."""


class InMemoryStateStore(StateStore):
    """Thread-safe in-memory implementation using asyncio locks."""

    def __init__(self) -> None:
        self._states: dict[str, CorrelationState] = {}
        self._triggered: set[str] = set()
        self._lock = asyncio.Lock()

    async def record_event(
        self,
        trade_id: str,
        source_system: str,
        payload: dict[str, Any],
        topic: str,
        timestamp: datetime,
        ttl_seconds: int,
        message_id: str | None = None,
    ) -> None:
        async with self._lock:
            now = time.time()
            if trade_id not in self._states:
                self._states[trade_id] = CorrelationState(
                    trade_id=trade_id,
                    created_at=now,
                    expires_at=now + ttl_seconds,
                )
            state = self._states[trade_id]
            state.expires_at = now + ttl_seconds
            state.events[source_system] = EventRecord(
                source_system=source_system,
                payload=payload,
                topic=topic,
                timestamp=timestamp,
                message_id=message_id,
            )

    async def get_state(self, trade_id: str) -> CorrelationState | None:
        async with self._lock:
            state = self._states.get(trade_id)
            if state is None:
                return None
            if time.time() > state.expires_at:
                return None
            return state

    async def has_triggered(self, trigger_key: str) -> bool:
        async with self._lock:
            return trigger_key in self._triggered

    async def mark_triggered(self, trigger_key: str) -> None:
        async with self._lock:
            self._triggered.add(trigger_key)

    async def sweep_expired(self) -> list[str]:
        async with self._lock:
            now = time.time()
            expired: list[str] = []
            for trade_id, state in list(self._states.items()):
                if now > state.expires_at:
                    expired.append(trade_id)
                    del self._states[trade_id]
                    self._triggered = {
                        k for k in self._triggered if not k.startswith(f"{trade_id}:")
                    }
            return expired

    async def delete_state(self, trade_id: str) -> None:
        async with self._lock:
            self._states.pop(trade_id, None)
            self._triggered = {
                k for k in self._triggered if not k.startswith(f"{trade_id}:")
            }

    async def get_all_active_trade_ids(self) -> list[str]:
        async with self._lock:
            now = time.time()
            return [
                tid for tid, s in self._states.items() if now <= s.expires_at
            ]


class RedisStateStore(StateStore):
    """Redis-backed implementation using hash sets and sorted sets for TTL."""

    def __init__(
        self, url: str = "redis://localhost:6379", key_prefix: str = "correlator:"
    ) -> None:
        self._url = url
        self._prefix = key_prefix
        self._redis: Any = None

    async def _get_redis(self) -> Any:
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
            except ImportError as e:
                raise RuntimeError(
                    "redis package required for RedisStateStore. "
                    "Install with: pip install event_correlator[redis]"
                ) from e
            self._redis = aioredis.from_url(self._url, decode_responses=True)
        return self._redis

    def _state_key(self, trade_id: str) -> str:
        return f"{self._prefix}state:{trade_id}"

    def _expiry_key(self) -> str:
        return f"{self._prefix}_expiry"

    def _triggered_key(self) -> str:
        return f"{self._prefix}_triggered"

    async def record_event(
        self,
        trade_id: str,
        source_system: str,
        payload: dict[str, Any],
        topic: str,
        timestamp: datetime,
        ttl_seconds: int,
        message_id: str | None = None,
    ) -> None:
        r = await self._get_redis()
        now = time.time()
        expires_at = now + ttl_seconds

        event_data = json.dumps({
            "source_system": source_system,
            "payload": payload,
            "topic": topic,
            "timestamp": timestamp.isoformat(),
            "message_id": message_id,
        })

        pipe = r.pipeline()
        pipe.hset(self._state_key(trade_id), source_system, event_data)
        pipe.hset(self._state_key(trade_id), "_created_at", str(now))
        pipe.hset(self._state_key(trade_id), "_expires_at", str(expires_at))
        pipe.expire(self._state_key(trade_id), ttl_seconds + 60)
        pipe.zadd(self._expiry_key(), {trade_id: expires_at})
        await pipe.execute()

    async def get_state(self, trade_id: str) -> CorrelationState | None:
        r = await self._get_redis()
        data = await r.hgetall(self._state_key(trade_id))
        if not data:
            return None

        now = time.time()
        expires_at = float(data.get("_expires_at", "0"))
        if now > expires_at:
            return None

        created_at = float(data.get("_created_at", str(now)))
        events: dict[str, EventRecord] = {}
        for key, value in data.items():
            if key.startswith("_"):
                continue
            event_json = json.loads(value)
            events[key] = EventRecord(
                source_system=event_json["source_system"],
                payload=event_json["payload"],
                topic=event_json["topic"],
                timestamp=datetime.fromisoformat(event_json["timestamp"]),
                message_id=event_json.get("message_id"),
            )

        return CorrelationState(
            trade_id=trade_id,
            events=events,
            created_at=created_at,
            expires_at=expires_at,
        )

    async def has_triggered(self, trigger_key: str) -> bool:
        r = await self._get_redis()
        return bool(await r.sismember(self._triggered_key(), trigger_key))

    async def mark_triggered(self, trigger_key: str) -> None:
        r = await self._get_redis()
        await r.sadd(self._triggered_key(), trigger_key)

    async def sweep_expired(self) -> list[str]:
        r = await self._get_redis()
        now = time.time()
        expired_members = await r.zrangebyscore(self._expiry_key(), "-inf", str(now))
        if not expired_members:
            return []

        pipe = r.pipeline()
        for trade_id in expired_members:
            pipe.delete(self._state_key(trade_id))
            pipe.zrem(self._expiry_key(), trade_id)
        await pipe.execute()

        # Clean triggered keys for expired trades
        triggered_members = await r.smembers(self._triggered_key())
        to_remove = [
            k for k in triggered_members
            if any(k.startswith(f"{tid}:") for tid in expired_members)
        ]
        if to_remove:
            await r.srem(self._triggered_key(), *to_remove)

        return list(expired_members)

    async def delete_state(self, trade_id: str) -> None:
        r = await self._get_redis()
        pipe = r.pipeline()
        pipe.delete(self._state_key(trade_id))
        pipe.zrem(self._expiry_key(), trade_id)
        await pipe.execute()

        triggered_members = await r.smembers(self._triggered_key())
        to_remove = [k for k in triggered_members if k.startswith(f"{trade_id}:")]
        if to_remove:
            await r.srem(self._triggered_key(), *to_remove)

    async def get_all_active_trade_ids(self) -> list[str]:
        r = await self._get_redis()
        now = time.time()
        return list(await r.zrangebyscore(self._expiry_key(), str(now), "+inf"))


def create_state_store(config: dict[str, Any]) -> StateStore:
    """Factory for creating state store instances from config."""
    store_type = config.get("type", "in_memory")
    if store_type == "redis":
        return RedisStateStore(
            url=config.get("url", "redis://localhost:6379"),
            key_prefix=config.get("key_prefix", "correlator:"),
        )
    if store_type == "in_memory":
        return InMemoryStateStore()
    raise ValueError(f"Unknown state store type: {store_type!r}. Use 'in_memory' or 'redis'.")
