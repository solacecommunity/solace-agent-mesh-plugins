"""
Dataiku API Client Wrapper

This module provides a reusable wrapper class for interacting with the Dataiku API.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Iterator
from datetime import datetime, timezone

try:
    import dataiku
    from dataiku.core.dss_llm import DSSLLMStreamedCompletionChunk, DSSLLMStreamedCompletionFooter
    DATAIKU_AVAILABLE = True
except ImportError:
    DATAIKU_AVAILABLE = False
    dataiku = None
    DSSLLMStreamedCompletionChunk = None
    DSSLLMStreamedCompletionFooter = None

log = logging.getLogger(__name__)


class DataikuClientError(Exception):
    """Base exception for Dataiku client errors"""
    pass


class DataikuAuthenticationError(DataikuClientError):
    """Raised when authentication fails"""
    pass


class DataikuConnectionError(DataikuClientError):
    """Raised when connection to Dataiku fails"""
    pass


class DataikuAgentNotFoundError(DataikuClientError):
    """Raised when specified agent is not found"""
    pass


class DataikuProjectNotFoundError(DataikuClientError):
    """Raised when specified project is not found"""
    pass


class DataikuClient:
    """
    Wrapper class for Dataiku API client operations.
    
    This class manages the Dataiku API client lifecycle and provides methods
    for interacting with Dataiku agents.
    """
    
    def __init__(
        self,
        instance_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_project_key: Optional[str] = None
    ):
        """
        Initialize the Dataiku client.
        
        Args:
            instance_url: Dataiku DSS instance URL (defaults to DATAIKU_INSTANCE_URL env var)
            api_key: API key for authentication (defaults to DATAIKU_API_KEY env var)
            default_project_key: Default project key (defaults to DATAIKU_DEFAULT_PROJECT env var)
        
        Raises:
            DataikuClientError: If Dataiku API client is not available
            DataikuAuthenticationError: If credentials are missing
        """
        if not DATAIKU_AVAILABLE:
            raise DataikuClientError(
                "Dataiku API client is not available. "
                "Please install it with: pip install dataiku-api-client"
            )
        
        self.instance_url = instance_url or os.getenv("DATAIKU_INSTANCE_URL")
        self.api_key = api_key or os.getenv("DATAIKU_API_KEY")
        self.default_project_key = default_project_key or os.getenv("DATAIKU_DEFAULT_PROJECT")
        
        if not self.instance_url:
            raise DataikuAuthenticationError(
                "Dataiku instance URL is required. "
                "Set DATAIKU_INSTANCE_URL environment variable or pass instance_url parameter."
            )
        
        if not self.api_key:
            raise DataikuAuthenticationError(
                "Dataiku API key is required. "
                "Set DATAIKU_API_KEY environment variable or pass api_key parameter."
            )
        
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """
        Initialize the Dataiku API client.
        
        Raises:
            DataikuConnectionError: If connection fails
        """
        try:
            # Set up Dataiku client with credentials
            os.environ["DATAIKU_API_KEY"] = self.api_key
            os.environ["DATAIKU_INSTANCE_URL"] = self.instance_url
            
            self._client = dataiku.api_client()
            log.info(f"[DataikuClient] Successfully initialized client for {self.instance_url}")
            
        except Exception as e:
            log.error(f"[DataikuClient] Failed to initialize client: {e}")
            raise DataikuConnectionError(f"Failed to connect to Dataiku: {str(e)}")
    
    def get_project(self, project_key: Optional[str] = None):
        """
        Get a Dataiku project.
        
        Args:
            project_key: Project key (uses default if not provided)
        
        Returns:
            Dataiku project object
        
        Raises:
            DataikuProjectNotFoundError: If project is not found
        """
        try:
            if project_key:
                project = self._client.get_project(project_key)
                log.info(f"[DataikuClient] Retrieved project: {project_key}")
            else:
                project = self._client.get_default_project()
                log.info("[DataikuClient] Retrieved default project")
            
            return project
            
        except Exception as e:
            log.error(f"[DataikuClient] Failed to get project: {e}")
            raise DataikuProjectNotFoundError(
                f"Project not found: {project_key or 'default'}. Error: {str(e)}"
            )
    
    def list_agents(self, project_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available agents in a project.
        
        Args:
            project_key: Project key (uses default if not provided)
        
        Returns:
            List of agent information dictionaries
        
        Raises:
            DataikuProjectNotFoundError: If project is not found
        """
        try:
            project = self.get_project(project_key)
            
            # Get list of LLMs (agents) in the project
            llms = project.list_llms()
            
            agents = []
            for llm_info in llms:
                agents.append({
                    "id": llm_info.get("id"),
                    "name": llm_info.get("name"),
                    "type": llm_info.get("type"),
                    "description": llm_info.get("description", "")
                })
            
            log.info(f"[DataikuClient] Found {len(agents)} agents in project")
            return agents
            
        except DataikuProjectNotFoundError:
            raise
        except Exception as e:
            log.error(f"[DataikuClient] Failed to list agents: {e}")
            return []
    
    def get_agent_metadata(
        self,
        agent_id: str,
        project_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get metadata for a specific agent.
        
        Args:
            agent_id: Agent ID (format: agent:xxxxxxxx)
            project_key: Project key (uses default if not provided)
        
        Returns:
            Agent metadata dictionary
        
        Raises:
            DataikuAgentNotFoundError: If agent is not found
        """
        try:
            project = self.get_project(project_key)
            llm = project.get_llm(agent_id)
            
            # Get agent settings/metadata
            settings = llm.get_settings()
            
            metadata = {
                "id": agent_id,
                "name": settings.get("name", agent_id),
                "type": settings.get("type", "unknown"),
                "description": settings.get("description", ""),
                "settings": settings
            }
            
            log.info(f"[DataikuClient] Retrieved metadata for agent: {agent_id}")
            return metadata
            
        except Exception as e:
            log.error(f"[DataikuClient] Failed to get agent metadata: {e}")
            raise DataikuAgentNotFoundError(
                f"Agent not found: {agent_id}. Error: {str(e)}"
            )
    
    def invoke_agent(
        self,
        agent_id: str,
        message: str,
        project_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke a Dataiku agent synchronously.
        
        Args:
            agent_id: Agent ID (format: agent:xxxxxxxx)
            message: Message to send to the agent
            project_key: Project key (uses default if not provided)
        
        Returns:
            Response dictionary with success, text, sources, and artifacts
        
        Raises:
            DataikuAgentNotFoundError: If agent is not found
        """
        try:
            project = self.get_project(project_key)
            llm = project.get_llm(agent_id)
            
            log.info(f"[DataikuClient] Invoking agent {agent_id} with message: {message[:100]}...")
            
            # Create completion and execute
            completion = llm.new_completion()
            resp = completion.with_message(message).execute()
            
            # Parse response
            result = {
                "success": resp.success,
                "text": resp.text if resp.success else "",
                "sources": [],
                "artifacts": [],
                "error": None if resp.success else "Agent execution failed",
                "metadata": {
                    "agent_id": agent_id,
                    "project_key": project_key or self.default_project_key,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "streaming": False
                }
            }
            
            # Extract sources if available
            if hasattr(resp, 'additionalInformation') and resp.additionalInformation:
                if 'sources' in resp.additionalInformation:
                    result["sources"] = resp.additionalInformation['sources']
                if 'artifacts' in resp.additionalInformation:
                    result["artifacts"] = resp.additionalInformation['artifacts']
            
            log.info(f"[DataikuClient] Agent invocation {'succeeded' if resp.success else 'failed'}")
            return result
            
        except Exception as e:
            log.error(f"[DataikuClient] Failed to invoke agent: {e}")
            return {
                "success": False,
                "text": "",
                "sources": [],
                "artifacts": [],
                "error": str(e),
                "metadata": {
                    "agent_id": agent_id,
                    "project_key": project_key or self.default_project_key,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "streaming": False
                }
            }
    
    def invoke_agent_streaming(
        self,
        agent_id: str,
        message: str,
        project_key: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Invoke a Dataiku agent with streaming responses.
        
        Args:
            agent_id: Agent ID (format: agent:xxxxxxxx)
            message: Message to send to the agent
            project_key: Project key (uses default if not provided)
        
        Yields:
            Response chunks as dictionaries
        
        Raises:
            DataikuAgentNotFoundError: If agent is not found
        """
        try:
            project = self.get_project(project_key)
            llm = project.get_llm(agent_id)
            
            log.info(f"[DataikuClient] Invoking agent {agent_id} with streaming...")
            
            # Create completion and execute with streaming
            completion = llm.new_completion()
            stream = completion.with_message(message).execute_streamed()
            
            sources = []
            artifacts = []
            full_text = ""
            
            for chunk in stream:
                if isinstance(chunk, DSSLLMStreamedCompletionChunk):
                    # Text chunk
                    full_text += chunk.text
                    yield {
                        "type": "chunk",
                        "text": chunk.text,
                        "success": True,
                        "metadata": {
                            "agent_id": agent_id,
                            "project_key": project_key or self.default_project_key,
                            "streaming": True
                        }
                    }
                    
                elif isinstance(chunk, DSSLLMStreamedCompletionFooter):
                    # Footer with sources and artifacts
                    if hasattr(chunk, 'additionalInformation') and chunk.additionalInformation:
                        if 'sources' in chunk.additionalInformation:
                            sources = chunk.additionalInformation['sources']
                        if 'artifacts' in chunk.additionalInformation:
                            artifacts = chunk.additionalInformation['artifacts']
            
            # Send final summary
            yield {
                "type": "complete",
                "success": True,
                "text": full_text,
                "sources": sources,
                "artifacts": artifacts,
                "error": None,
                "metadata": {
                    "agent_id": agent_id,
                    "project_key": project_key or self.default_project_key,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "streaming": True
                }
            }
            
            log.info("[DataikuClient] Streaming invocation completed successfully")
            
        except Exception as e:
            log.error(f"[DataikuClient] Failed to invoke agent with streaming: {e}")
            yield {
                "type": "error",
                "success": False,
                "text": "",
                "sources": [],
                "artifacts": [],
                "error": str(e),
                "metadata": {
                    "agent_id": agent_id,
                    "project_key": project_key or self.default_project_key,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "streaming": True
                }
            }
    
    def test_connection(self) -> bool:
        """
        Test the connection to Dataiku.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to get default project as a connection test
            self.get_project()
            log.info("[DataikuClient] Connection test successful")
            return True
        except Exception as e:
            log.error(f"[DataikuClient] Connection test failed: {e}")
            return False