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
        try:
            super()._initialize_flows()
        except (ValueError, Exception) as exc:
            friendly = self._get_friendly_broker_error(exc)
            if friendly:
                print(f"\n  Error: {friendly}\n")
                sys.exit(1)
            raise

    def _get_friendly_broker_error(self, exc: Exception) -> str:
        """Extract a user-friendly message from broker-related exceptions."""
        # Walk the exception chain to find the root cause details
        messages = []
        current = exc
        while current:
            messages.append(str(current))
            current = current.__cause__ or current.__context__

        full_error = " ".join(messages)
        gateway_id = self.app_info.get("app_config", {}).get(
            "gateway_id", "unknown"
        )
        broker_url = self.app_info.get("broker", {}).get(
            "broker_url", "unknown"
        )

        if "Max clients exceeded" in full_error:
            return (
                f"Could not start CLI entrypoint '{gateway_id}'.\n"
                f"  Another process is already connected to this gateway's broker queue.\n\n"
                f"  To fix, either:\n"
                f"    1. Stop the other process using gateway '{gateway_id}', or\n"
                f"    2. Use a different gateway ID:\n"
                f"       CLI_ENTRYPOINT_ID=sam-cli-ep-02 sam run <config.yaml>"
            )

        if "Login Failure" in full_error or "UNAUTHORIZED" in full_error.upper():
            return (
                f"Broker authentication failed for '{broker_url}'.\n"
                f"  Check SOLACE_BROKER_USERNAME, SOLACE_BROKER_PASSWORD, and SOLACE_BROKER_VPN\n"
                f"  in your .env file or environment."
            )

        if "Unknown Host" in full_error or "Connection refused" in full_error.lower():
            return (
                f"Cannot reach broker at '{broker_url}'.\n"
                f"  Ensure the broker is running and SOLACE_BROKER_URL is correct."
            )

        if "Timed Out" in full_error or "timed out" in full_error.lower():
            return (
                f"Connection to broker at '{broker_url}' timed out.\n"
                f"  Check that the broker is reachable and not overloaded."
            )

        if "broker connection" in full_error.lower():
            return (
                f"Could not connect to broker at '{broker_url}'.\n"
                f"  Details: {messages[-1] if len(messages) > 1 else messages[0]}"
            )

        return None

    def _get_gateway_component_class(self) -> type[BaseGatewayComponent]:
        return CliEntrypointComponent
