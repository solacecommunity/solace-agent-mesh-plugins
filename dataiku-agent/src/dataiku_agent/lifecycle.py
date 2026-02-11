"""
Dataiku Agent Lifecycle Functions

This module contains initialization and cleanup functions for the Dataiku Agent.
"""

import logging
from typing import Any, Dict, Optional

from .utils.dataiku_client import (
    DataikuClient,
    DataikuClientError,
    DataikuAuthenticationError,
    DataikuConnectionError
)

log = logging.getLogger(__name__)


async def initialize_dataiku_agent(
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Initialize the Dataiku Agent.
    
    This function is called when the agent starts up. It validates the Dataiku
    credentials and tests the connection to ensure everything is configured correctly.
    
    Args:
        tool_context: Optional tool context from SAM
        tool_config: Optional tool configuration containing startup settings
    
    Returns:
        Dict containing initialization status and any relevant information
    """
    log_identifier = "[initialize_dataiku_agent]"
    
    startup_message = (tool_config or {}).get(
        "startup_message",
        "Dataiku Agent is initializing..."
    )
    
    log.info(f"{log_identifier} {startup_message}")
    
    try:
        # Attempt to create and test the Dataiku client
        client = DataikuClient()
        
        log.info(f"{log_identifier} Testing connection to Dataiku instance: {client.instance_url}")
        
        # Test the connection
        connection_ok = client.test_connection()
        
        if connection_ok:
            log.info(f"{log_identifier} Successfully connected to Dataiku")
            
            # Try to get some basic info
            try:
                agents = client.list_agents()
                agent_count = len(agents)
                log.info(f"{log_identifier} Found {agent_count} available agents")
                
                return {
                    "status": "success",
                    "message": f"Dataiku Agent initialized successfully. Connected to {client.instance_url}",
                    "instance_url": client.instance_url,
                    "default_project": client.default_project_key,
                    "available_agents": agent_count,
                    "connection_tested": True
                }
            except Exception as e:
                log.warning(f"{log_identifier} Could not list agents during initialization: {e}")
                return {
                    "status": "success",
                    "message": f"Dataiku Agent initialized. Connected to {client.instance_url}",
                    "instance_url": client.instance_url,
                    "default_project": client.default_project_key,
                    "connection_tested": True,
                    "warning": "Could not list agents during initialization"
                }
        else:
            log.error(f"{log_identifier} Connection test failed")
            return {
                "status": "error",
                "message": "Failed to connect to Dataiku instance",
                "instance_url": client.instance_url,
                "connection_tested": False
            }
    
    except DataikuAuthenticationError as e:
        log.error(f"{log_identifier} Authentication error during initialization: {e}")
        return {
            "status": "error",
            "message": f"Authentication failed: {str(e)}",
            "error_type": "authentication",
            "help": "Please check DATAIKU_INSTANCE_URL and DATAIKU_API_KEY environment variables"
        }
    
    except DataikuConnectionError as e:
        log.error(f"{log_identifier} Connection error during initialization: {e}")
        return {
            "status": "error",
            "message": f"Connection failed: {str(e)}",
            "error_type": "connection",
            "help": "Please check your Dataiku instance URL and network connectivity"
        }
    
    except DataikuClientError as e:
        log.error(f"{log_identifier} Client error during initialization: {e}")
        return {
            "status": "error",
            "message": f"Client initialization failed: {str(e)}",
            "error_type": "client",
            "help": "Please ensure dataiku-api-client is installed: pip install dataiku-api-client"
        }
    
    except Exception as e:
        log.error(f"{log_identifier} Unexpected error during initialization: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "unknown"
        }


async def cleanup_dataiku_agent(
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Cleanup the Dataiku Agent.
    
    This function is called when the agent is shutting down. It performs any
    necessary cleanup operations.
    
    Args:
        tool_context: Optional tool context from SAM
        tool_config: Optional tool configuration
    
    Returns:
        Dict containing cleanup status
    """
    log_identifier = "[cleanup_dataiku_agent]"
    log.info(f"{log_identifier} Cleaning up Dataiku Agent...")
    
    try:
        # Currently no specific cleanup needed for Dataiku client
        # This is a placeholder for future cleanup operations
        
        log.info(f"{log_identifier} Dataiku Agent cleanup completed successfully")
        
        return {
            "status": "success",
            "message": "Dataiku Agent cleaned up successfully"
        }
    
    except Exception as e:
        log.error(f"{log_identifier} Error during cleanup: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Cleanup error: {str(e)}"
        }