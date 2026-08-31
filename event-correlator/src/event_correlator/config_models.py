"""Pydantic configuration models for the Event Correlator plugin."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CorrelationKeyExtraction(BaseModel):
    method: Literal["json_path", "topic_position"] = "json_path"
    expression: str = "$.tradeId"
    position: int | None = None


class SubscriptionConfig(BaseModel):
    topic: str


class SourceSystemConfig(BaseModel):
    name: str
    subscriptions: list[SubscriptionConfig]
    correlation_key_extraction: CorrelationKeyExtraction


class AllSourcesPresentRuleConfig(BaseModel):
    type: Literal["all_sources_present"] = "all_sources_present"
    required_sources: list[str] = Field(
        default_factory=lambda: ["system_a", "system_b", "system_c"]
    )


class ImmediateOnSourceRuleConfig(BaseModel):
    type: Literal["immediate_on_source"] = "immediate_on_source"
    source: str = "system_b"
    topic_pattern: str = "events/system-b-changes/>"


class CorrelationConfig(BaseModel):
    ttl_seconds: int = Field(default=86400, ge=1)
    ttl_sweep_interval_ms: int = Field(default=30000, ge=1000)
    ttl_expiry_action: Literal["drop", "alert", "trigger_partial"] = "alert"
    trigger_rules: list[dict] = Field(default_factory=list)


class StateStoreConfig(BaseModel):
    type: Literal["in_memory", "redis", "database"] = "in_memory"
    url: str = "redis://localhost:6379"
    connection_string: str = "sqlite:///correlator_state.db"
    key_prefix: str = "correlator:"


class OutputConfig(BaseModel):
    success_topic_pattern: str = "correlator/results/{trade_id}"
    error_topic_pattern: str = "correlator/errors/{trade_id}"


class DataPlaneBrokerConfig(BaseModel):
    broker_url: str = "ws://localhost:8008"
    broker_vpn: str = "default"
    broker_username: str = "default"
    broker_password: str = "default"
    dev_mode: bool = False


class CorrelatorPluginConfig(BaseModel):
    gateway_id: str = "event-correlator-01"
    namespace: str = "SAM/"
    data_plane_broker_config: DataPlaneBrokerConfig = Field(
        default_factory=DataPlaneBrokerConfig
    )
    source_systems: list[SourceSystemConfig]
    correlation_config: CorrelationConfig = Field(default_factory=CorrelationConfig)
    state_store: StateStoreConfig = Field(default_factory=StateStoreConfig)
    target_agent_name: str = "ReconciliationAgent"
    default_user_identity: str = "event-correlator-service"
    output_config: OutputConfig = Field(default_factory=OutputConfig)
