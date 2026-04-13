import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .web_server import ArtifactWebServer, set_web_server

logger = logging.getLogger(__name__)


def init_function(host_component: Any, config: Optional[Dict[str, Any]] = None) -> None:
    """
    Initialize and start the web server when the agent starts.

    This function is called during agent initialization to set up the
    artifact hosting web server.

    Args:
        host_component: The host component (not used)
        config: Configuration dictionary with optional parameters:
            - port: Port to bind the web server (default: 8080)
            - host: Host to bind to (default: 127.0.0.1)
            - host_directory: Directory to serve files from (default: ./hosted_files)
            - base_url: Custom base URL for proxies/firewalls (optional)
    """
    logger.info("[ArtifactHost:init] Starting artifact hosting web server")

    # Get configuration
    current_config = config if config is not None else {}
    port = current_config.get("port", 8080)
    host = current_config.get("host", "127.0.0.1")
    host_directory = current_config.get("host_directory", "./hosted_files")

    # Convert host_directory to Path
    host_dir_path = Path(host_directory)
    if not host_dir_path.is_absolute():
        # Make it relative to current working directory
        host_dir_path = Path.cwd() / host_dir_path

    logger.info(f"[ArtifactHost:init] Configuration: port={port}, host={host}, directory={host_dir_path}")

    # Create and start web server
    try:
        web_server = ArtifactWebServer(
            host_directory=host_dir_path,
            port=port,
            host=host
        )

        web_server.start()
        set_web_server(web_server)

        logger.info(f"[ArtifactHost:init] Web server started successfully on http://{host}:{port}")
        logger.info(f"[ArtifactHost:init] Files will be hosted from: {host_dir_path}")

        base_url = current_config.get("base_url")
        if base_url:
            logger.info(f"[ArtifactHost:init] Custom base URL configured: {base_url}")

    except Exception as e:
        logger.error(f"[ArtifactHost:init] Failed to start web server: {e}")
        raise


def cleanup_function(host_component: Any, config: Optional[Dict[str, Any]] = None) -> None:
    """
    Cleanup function called when the agent shuts down.

    Attempts to gracefully stop the web server.

    Args:
        host_component: The host component (not used)
        config: Configuration dictionary (not currently used)
    """
    logger.info("[ArtifactHost:cleanup] Shutting down artifact hosting web server")

    from .web_server import get_web_server

    web_server = get_web_server()
    if web_server:
        web_server.stop()
        logger.info("[ArtifactHost:cleanup] Web server shutdown complete")
    else:
        logger.warning("[ArtifactHost:cleanup] No web server instance found")
