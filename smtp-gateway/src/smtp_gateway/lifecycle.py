"""
SMTP Gateway Lifecycle Functions

This module contains initialization and cleanup functions for the SMTP Gateway Agent.
"""

import asyncio
from typing import Any
from datetime import datetime, timezone
from solace_ai_connector.common.log import log


def initialize_smtp_gateway(host_component: Any):
    """
    Initialize the SMTP Gateway Agent.
    
    Args:
        host_component: The agent host component
    """
    log_identifier = f"[{host_component.agent_name}:init]"
    log.info(f"{log_identifier} Starting SMTP Gateway Agent initialization...")
    
    try:
        # Store initialization metadata
        host_component.set_agent_specific_state("initialized_at", datetime.now(timezone.utc).isoformat())
        host_component.set_agent_specific_state("emails_sent_count", 0)
        host_component.set_agent_specific_state("emails_received_count", 0)
        host_component.set_agent_specific_state("agent_version", "0.1.0")
        
        # Get configuration from agent_init_function config
        config = host_component.get_config().get("agent_init_function", {}).get("config", {})
        
        # Store service configuration
        service_config = {
            "max_attachment_size_mb": config.get("max_attachment_size_mb", 25),
            "allowed_attachment_types": config.get("allowed_attachment_types", [
                "pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "gif", "zip"
            ]),
            "startup_message": config.get("startup_message", "SMTP Gateway Agent initialized")
        }
        host_component.set_agent_specific_state("service_config", service_config)
        
        # Log startup message
        log.info(f"{log_identifier} {service_config['startup_message']}")
        log.info(f"{log_identifier} Max attachment size: {service_config['max_attachment_size_mb']}MB")
        log.info(f"{log_identifier} Allowed attachment types: {', '.join(service_config['allowed_attachment_types'])}")
        log.info(f"{log_identifier} SMTP Gateway Agent initialization completed successfully")
        
    except Exception as e:
        log.error(f"{log_identifier} Failed to initialize SMTP Gateway Agent: {e}")
        raise


def cleanup_smtp_gateway(host_component: Any):
    """
    Clean up SMTP Gateway Agent resources.
    
    Args:
        host_component: The agent host component
    """
    log_identifier = f"[{host_component.agent_name}:cleanup]"
    log.info(f"{log_identifier} Starting SMTP Gateway Agent cleanup...")

    async def cleanup_async(host_component: Any):
        try:
            # Get final statistics
            emails_sent = host_component.get_agent_specific_state("emails_sent_count", 0)
            emails_received = host_component.get_agent_specific_state("emails_received_count", 0)
            initialized_at = host_component.get_agent_specific_state("initialized_at", "unknown")
            
            log.info(f"{log_identifier} Agent sent {emails_sent} emails during its lifetime")
            log.info(f"{log_identifier} Agent received {emails_received} emails during its lifetime")
            log.info(f"{log_identifier} Agent was initialized at: {initialized_at}")
            
            # Clean up any remaining resources
            # Note: Connection cleanup is handled automatically by the service layer
            
            log.info(f"{log_identifier} SMTP Gateway Agent cleanup completed successfully")
        
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
    
    log.info(f"{log_identifier} SMTP Gateway Agent cleanup completed")