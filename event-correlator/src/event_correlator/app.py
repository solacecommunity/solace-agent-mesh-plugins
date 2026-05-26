"""CorrelatorApp — SAM Gateway App for multi-source event correlation."""

from __future__ import annotations

import logging
from typing import Any

from solace_agent_mesh.gateway.base.app import BaseGatewayApp, BaseGatewayComponent

log = logging.getLogger(__name__)

info = {
    "class_name": "CorrelatorApp",
    "description": "Event Correlator Gateway — correlates events across multiple source systems",
}


class CorrelatorApp(BaseGatewayApp):
    """Gateway app that correlates events from N source systems and triggers an agent."""

    SPECIFIC_APP_SCHEMA_PARAMS: list[dict[str, Any]] = [
        {
            "name": "data_plane_broker_config",
            "required": True,
            "type": "object",
            "description": "Broker config for the data-plane Solace client (source system events).",
        },
        {
            "name": "source_systems",
            "required": True,
            "type": "list",
            "description": "List of source system subscription configurations.",
        },
        {
            "name": "correlation_config",
            "required": True,
            "type": "object",
            "description": "Correlation key extraction, TTL, and trigger rules.",
        },
        {
            "name": "state_store",
            "required": False,
            "type": "object",
            "default": {"type": "in_memory"},
            "description": "State store configuration (in_memory or redis).",
        },
        {
            "name": "target_agent_name",
            "required": True,
            "type": "string",
            "description": "Name of the agent to invoke via A2A when a trigger fires.",
        },
        {
            "name": "output_config",
            "required": False,
            "type": "object",
            "default": {
                "success_topic_pattern": "correlator/results/{trade_id}",
                "error_topic_pattern": "correlator/errors/{trade_id}",
            },
            "description": "Output topic patterns for publishing correlation results.",
        },
    ]

    def __init__(self, app_info: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(app_info=app_info, **kwargs)

    def _get_gateway_component_class(self) -> type[BaseGatewayComponent]:
        from .component import CorrelatorComponent

        return CorrelatorComponent
