"""
Dataiku Agent Tools

This module contains the tools for the Dataiku Agent following SAM patterns.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from .utils.dataiku_client import (
    DataikuClient,
    DataikuClientError,
    DataikuAuthenticationError,
    DataikuConnectionError,
    DataikuAgentNotFoundError,
    DataikuProjectNotFoundError
)

log = logging.getLogger(__name__)


async def invoke_dataiku_agent(
    agent_id: str,
    message: str,
    project_key: Optional[str] = None,
    stream: bool = False,
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Invoke a Dataiku AI agent with a message.
    
    This is the main tool for interacting with Dataiku agents. It sends a message
    to the specified agent and returns the response, including any sources or
    artifacts provided by the agent.
    
    Args:
        agent_id: The Dataiku agent ID (format: agent:xxxxxxxx)
        message: The message to send to the agent
        project_key: Optional project key (uses default if not provided)
        stream: Whether to use streaming responses (default: False)
        tool_context: Optional tool context from SAM
        tool_config: Optional tool configuration
    
    Returns:
        Dict containing:
            - success (bool): Whether the invocation succeeded
            - text (str): The agent response text
            - sources (list): Optional source documents
            - artifacts (list): Optional artifacts
            - error (str): Error message if invocation failed
            - metadata (dict): Additional metadata about the invocation
    """
    log_identifier = "[invoke_dataiku_agent]"
    log.info(f"{log_identifier} Invoking agent {agent_id} with message: {message[:100]}...")
    
    try:
        # Initialize Dataiku client
        client = DataikuClient()
        
        if stream:
            # Handle streaming response
            log.info(f"{log_identifier} Using streaming mode")
            
            # Collect all chunks
            chunks = []
            final_result = None
            
            def _invoke_streaming():
                return list(client.invoke_agent_streaming(agent_id, message, project_key))
            
            # Run in thread to avoid blocking
            results = await asyncio.to_thread(_invoke_streaming)
            
            for result in results:
                if result.get("type") == "complete":
                    final_result = result
                    break
            
            if final_result:
                return final_result
            else:
                return {
                    "success": False,
                    "text": "",
                    "sources": [],
                    "artifacts": [],
                    "error": "Streaming completed without final result",
                    "metadata": {
                        "agent_id": agent_id,
                        "project_key": project_key,
                        "streaming": True
                    }
                }
        else:
            # Handle synchronous response
            log.info(f"{log_identifier} Using synchronous mode")
            
            def _invoke():
                return client.invoke_agent(agent_id, message, project_key)
            
            # Run in thread to avoid blocking
            result = await asyncio.to_thread(_invoke)
            
            log.info(f"{log_identifier} Invocation {'succeeded' if result['success'] else 'failed'}")
            return result
    
    except DataikuAuthenticationError as e:
        log.error(f"{log_identifier} Authentication error: {e}")
        return {
            "success": False,
            "text": "",
            "sources": [],
            "artifacts": [],
            "error": f"Authentication failed: {str(e)}. Please check DATAIKU_INSTANCE_URL and DATAIKU_API_KEY environment variables.",
            "metadata": {
                "agent_id": agent_id,
                "project_key": project_key,
                "streaming": stream
            }
        }
    
    except DataikuAgentNotFoundError as e:
        log.error(f"{log_identifier} Agent not found: {e}")
        return {
            "success": False,
            "text": "",
            "sources": [],
            "artifacts": [],
            "error": f"Agent not found: {str(e)}. Use list_dataiku_agents to see available agents.",
            "metadata": {
                "agent_id": agent_id,
                "project_key": project_key,
                "streaming": stream
            }
        }
    
    except DataikuProjectNotFoundError as e:
        log.error(f"{log_identifier} Project not found: {e}")
        return {
            "success": False,
            "text": "",
            "sources": [],
            "artifacts": [],
            "error": f"Project not found: {str(e)}. Please check the project_key or DATAIKU_DEFAULT_PROJECT environment variable.",
            "metadata": {
                "agent_id": agent_id,
                "project_key": project_key,
                "streaming": stream
            }
        }
    
    except DataikuConnectionError as e:
        log.error(f"{log_identifier} Connection error: {e}")
        return {
            "success": False,
            "text": "",
            "sources": [],
            "artifacts": [],
            "error": f"Connection failed: {str(e)}. Please check your Dataiku instance URL and network connectivity.",
            "metadata": {
                "agent_id": agent_id,
                "project_key": project_key,
                "streaming": stream
            }
        }
    
    except Exception as e:
        log.error(f"{log_identifier} Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "text": "",
            "sources": [],
            "artifacts": [],
            "error": f"Unexpected error: {str(e)}",
            "metadata": {
                "agent_id": agent_id,
                "project_key": project_key,
                "streaming": stream
            }
        }


async def list_dataiku_agents(
    project_key: Optional[str] = None,
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    List available Dataiku agents in a project.
    
    This tool helps discover what agents are available in your Dataiku project.
    Use this to find agent IDs before invoking them.
    
    Args:
        project_key: Optional project key (uses default if not provided)
        tool_context: Optional tool context from SAM
        tool_config: Optional tool configuration
    
    Returns:
        Dict containing:
            - success (bool): Whether the listing succeeded
            - agents (list): List of agent information dictionaries
            - count (int): Number of agents found
            - error (str): Error message if listing failed
    """
    log_identifier = "[list_dataiku_agents]"
    log.info(f"{log_identifier} Listing agents in project: {project_key or 'default'}")
    
    try:
        # Initialize Dataiku client
        client = DataikuClient()
        
        def _list_agents():
            return client.list_agents(project_key)
        
        # Run in thread to avoid blocking
        agents = await asyncio.to_thread(_list_agents)
        
        log.info(f"{log_identifier} Found {len(agents)} agents")
        
        return {
            "success": True,
            "agents": agents,
            "count": len(agents),
            "error": None,
            "project_key": project_key or client.default_project_key
        }
    
    except DataikuAuthenticationError as e:
        log.error(f"{log_identifier} Authentication error: {e}")
        return {
            "success": False,
            "agents": [],
            "count": 0,
            "error": f"Authentication failed: {str(e)}. Please check DATAIKU_INSTANCE_URL and DATAIKU_API_KEY environment variables."
        }
    
    except DataikuProjectNotFoundError as e:
        log.error(f"{log_identifier} Project not found: {e}")
        return {
            "success": False,
            "agents": [],
            "count": 0,
            "error": f"Project not found: {str(e)}. Please check the project_key or DATAIKU_DEFAULT_PROJECT environment variable."
        }
    
    except Exception as e:
        log.error(f"{log_identifier} Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "agents": [],
            "count": 0,
            "error": f"Unexpected error: {str(e)}"
        }


async def get_agent_info(
    agent_id: str,
    project_key: Optional[str] = None,
    tool_context: Optional[Any] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific Dataiku agent.
    
    This tool retrieves metadata and configuration details for a specific agent,
    helping you understand its capabilities before invoking it.
    
    Args:
        agent_id: The Dataiku agent ID (format: agent:xxxxxxxx)
        project_key: Optional project key (uses default if not provided)
        tool_context: Optional tool context from SAM
        tool_config: Optional tool configuration
    
    Returns:
        Dict containing:
            - success (bool): Whether the retrieval succeeded
            - agent_info (dict): Agent metadata and configuration
            - error (str): Error message if retrieval failed
    """
    log_identifier = "[get_agent_info]"
    log.info(f"{log_identifier} Getting info for agent: {agent_id}")
    
    try:
        # Initialize Dataiku client
        client = DataikuClient()
        
        def _get_metadata():
            return client.get_agent_metadata(agent_id, project_key)
        
        # Run in thread to avoid blocking
        metadata = await asyncio.to_thread(_get_metadata)
        
        log.info(f"{log_identifier} Successfully retrieved agent info")
        
        return {
            "success": True,
            "agent_info": metadata,
            "error": None
        }
    
    except DataikuAuthenticationError as e:
        log.error(f"{log_identifier} Authentication error: {e}")
        return {
            "success": False,
            "agent_info": {},
            "error": f"Authentication failed: {str(e)}. Please check DATAIKU_INSTANCE_URL and DATAIKU_API_KEY environment variables."
        }
    
    except DataikuAgentNotFoundError as e:
        log.error(f"{log_identifier} Agent not found: {e}")
        return {
            "success": False,
            "agent_info": {},
            "error": f"Agent not found: {str(e)}. Use list_dataiku_agents to see available agents."
        }
    
    except DataikuProjectNotFoundError as e:
        log.error(f"{log_identifier} Project not found: {e}")
        return {
            "success": False,
            "agent_info": {},
            "error": f"Project not found: {str(e)}. Please check the project_key or DATAIKU_DEFAULT_PROJECT environment variable."
        }
    
    except Exception as e:
        log.error(f"{log_identifier} Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "agent_info": {},
            "error": f"Unexpected error: {str(e)}"
        }