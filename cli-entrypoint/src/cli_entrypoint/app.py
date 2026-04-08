"""
Custom App class for the CLI Entrypoint.
"""

import logging
import sys
from typing import Any, Dict, List

from solace_agent_mesh.gateway.base.app import BaseGatewayApp
from solace_agent_mesh.gateway.base.component import BaseGatewayComponent

from cli_entrypoint.component import CliEntrypointComponent

log = logging.getLogger(__name__)

info = {
    "class_name": "CliEntrypointApp",
    "description": "Custom App class for the CLI Entrypoint adapter.",
}


class CliEntrypointApp(BaseGatewayApp):
    """
    Custom App class for the CLI Entrypoint.
    Extends BaseGatewayApp for common gateway functionalities.
    """

    SPECIFIC_APP_SCHEMA_PARAMS: List[Dict[str, Any]] = [
        {
            "name": "adapter_config",
            "required": False,
            "type": "object",
            "default": {},
            "description": "CLI adapter-specific configuration (prompt, user_id, show_status_updates).",
        },
        {
            "name": "default_agent_name",
            "required": False,
            "type": "string",
            "default": "OrchestratorAgent",
            "description": "Default agent to route messages to.",
        },
        {
            "name": "system_purpose",
            "required": False,
            "type": "string",
            "default": "",
            "description": "System purpose description for agents.",
        },
        {
            "name": "response_format",
            "required": False,
            "type": "string",
            "default": "",
            "description": "Response format guidelines for agents.",
        },
        {
            "name": "authorization_service",
            "required": False,
            "type": "object",
            "default": {"type": "none"},
            "description": "Authorization service configuration.",
        },
    ]

    def __init__(self, app_info: Dict[str, Any], **kwargs):
        config_files = [f for f in sys.argv[1:] if f.endswith((".yaml", ".yml"))]
        self._skip_initialization = len(config_files) > 1
        super().__init__(app_info=app_info, **kwargs)

    def _initialize_flows(self):
        if self._skip_initialization:
            log.info(
                "CLI entrypoint: skipping flow initialization (multi-config SAM run). "
                "To use the CLI, launch it separately: "
                "sam run configs/gateways/cli-entrypoint.yaml"
            )
            return
        super()._initialize_flows()

    def _get_gateway_component_class(self) -> type[BaseGatewayComponent]:
        return CliEntrypointComponent
