"""
Custom App class for the CLI Entrypoint.
"""

from typing import Any, Dict, List

from solace_agent_mesh.gateway.base.app import BaseGatewayApp
from solace_agent_mesh.gateway.base.component import BaseGatewayComponent

from cli_entrypoint.component import CliEntrypointComponent


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
        super().__init__(app_info=app_info, **kwargs)

    def _get_gateway_component_class(self) -> type[BaseGatewayComponent]:
        return CliEntrypointComponent
