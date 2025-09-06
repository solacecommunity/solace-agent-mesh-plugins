"""
Find My IP Agent Lifecycle Functions

This module contains initialization and cleanup functions for the Find My IP Agent.
"""

import asyncio
from typing import Any
from solace_ai_connector.common.log import log


def initialize_find_my_ip(host_component: Any):
    """
    Initialize the Find My IP Agent.
    
    Args:
        host_component: The agent host component
    """
    log_identifier = f"[{host_component.agent_name}:init]"
    log.info(f"{log_identifier} Starting Find My IP Agent initialization...")
    
    try:
        # Store initialization metadata
        host_component.set_agent_specific_state("initialized_at", "2024-01-01T00:00:00Z")
        host_component.set_agent_specific_state("ip_requests_count", 0)
        host_component.set_agent_specific_state("agent_version", "1.0.0")
        
        # Initialize service configuration
        service_config = {
            "ipify_url": "https://api.ipify.org?format=json",
            "location_url": "https://ipapi.co",
            "timeout": 10,
            "max_retries": 3
        }
        host_component.set_agent_specific_state("service_config", service_config)
        
        # Log startup message
        log.info(f"{log_identifier} Find My IP Agent initialization completed successfully")
        log.info(f"{log_identifier} Agent is ready to provide IP address information")
        
    except Exception as e:
        log.error(f"{log_identifier} Failed to initialize Find My IP Agent: {e}")
        raise


def cleanup_find_my_ip(host_component: Any):
    """
    Clean up Find My IP Agent resources.
    
    Args:
        host_component: The agent host component
    """
    log_identifier = f"[{host_component.agent_name}:cleanup]"
    log.info(f"{log_identifier} Starting Find My IP Agent cleanup...")

    async def cleanup_async(host_component: Any):
        try:
            # Get final statistics
            request_count = host_component.get_agent_specific_state("ip_requests_count", 0)
            initialized_at = host_component.get_agent_specific_state("initialized_at", "unknown")
            
            log.info(f"{log_identifier} Agent processed {request_count} IP requests during its lifetime")
            log.info(f"{log_identifier} Agent was initialized at: {initialized_at}")
            
            # Clean up any remaining resources
            # Note: Service cleanup is handled automatically by the service layer
            
            log.info(f"{log_identifier} Find My IP Agent cleanup completed successfully")
        
        except Exception as e:
            log.error(f"{log_identifier} Error during cleanup: {e}")
    
    # Run cleanup in the event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a task
            asyncio.create_task(cleanup_async(host_component))
        else:
            # Otherwise, run until complete
            loop.run_until_complete(cleanup_async(host_component))
    except RuntimeError:
        # If no event loop is available, create a new one
        asyncio.run(cleanup_async(host_component))
    
    log.info(f"{log_identifier} Find My IP Agent cleanup completed")
