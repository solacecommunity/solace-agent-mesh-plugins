# Event Correlator

**Plugin Type:** Gateway

## Overview

A SAM Gateway plugin that correlates events from N source systems by a shared key (e.g., `orderId`, `tradeId`, `requestId`) and triggers a downstream agent via A2A when configurable conditions are met.

Use cases include trade reconciliation, multi-system order matching, distributed transaction tracking, and any workflow where events from independent systems must be joined before processing.

## Features

- Correlate events from any number of source systems by a configurable key
- Two built-in trigger rules (extensible):
  - **All sources present**: fire when every configured source has published for the same key
  - **Immediate on source**: fire immediately when a specific source publishes (e.g., change/amendment events)
- Pluggable state store (in-memory, Redis, or PostgreSQL/SQLite via SAM's CacheService)
- Idempotent trigger evaluation (no double-firing on redelivery)
- Configurable TTL with expiry actions (drop, alert, trigger with partial data)
- Output publishing to configurable Solace topics
- Correlation key extraction via JSON path or topic position
- Structured logging with correlation key on every log line

## Installation

```bash
sam plugin add event-correlator --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins.git#subdirectory=event-correlator
```

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Description | Default |
|----------|-------------|---------|
| `SOLACE_BROKER_URL` | SAM control-plane broker | `ws://localhost:8008` |
| `DATA_PLANE_BROKER_URL` | Source system event broker | Same as control-plane |
| `REDIS_URL` | Redis for production state store | `redis://localhost:6379` |
| `TARGET_AGENT_NAME` | Agent to invoke when a trigger fires | `MyReconciliationAgent` |
| `CORRELATOR_GATEWAY_ID` | Gateway instance ID | `event-correlator-01` |

See `config.yaml` for full configuration options including source system subscriptions, correlation key extraction methods, trigger rules, TTL settings, and output topic patterns.

## Trigger Rules

### All Sources Present
Fires when all configured source systems have published an event for the same correlation key within the TTL window. The set of required sources is configurable.

### Immediate on Source
Fires immediately when a specific source system publishes an event matching a topic pattern (e.g., change/amendment events). Useful when an agent should react to a single event without waiting for the full correlation set.

## How It Works

```
Source System A ──► Solace Broker ──┐
Source System B ──► Solace Broker ──┼──► Event Correlator Gateway ──► Agent (A2A)
Source System C ──► Solace Broker ──┘         │
                                              ▼
                                        State Store
                                      (InMemory/Redis)
```

1. Events arrive on configurable topic patterns (one or more per source system)
2. The correlator extracts the correlation key (JSON path or topic position)
3. State is accumulated per key across all source systems
4. Trigger rules evaluate after each event ingestion
5. When a rule fires, the correlator invokes the target agent via A2A with the full correlated payload

## Development

```bash
pip install -e ".[dev,redis]"
pytest
ruff check src/ tests/
```

## State Store Options

| Type | Config | Use Case |
|------|--------|----------|
| `in_memory` | `type: "in_memory"` | Development, single instance |
| `redis` | `type: "redis"`, `url: "redis://..."` | Production, multi-instance |
| `database` | `type: "database"`, `connection_string: "postgresql://..."` | Production, uses SAM's built-in CacheService (PostgreSQL/SQLite) |

The `database` store uses SAM's `CacheService` with `SQLAlchemyStorage`, sharing the same database infrastructure as SAM's session and task state. No additional dependencies required when running within SAM.

## Limitations

- ACK-on-receive strategy means events can be lost if the process crashes between ACK and state persistence. Use `database` or `redis` state store with durable queues in production.
- Queue creation is out of scope — broker admin must provision durable queues with appropriate topic subscriptions.
- The correlator does NOT call external APIs or MCP. If the target agent needs additional context, it should fetch that itself.
