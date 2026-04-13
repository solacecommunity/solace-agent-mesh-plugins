import logging
import asyncio
import inspect
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.adk.tools import ToolContext
from solace_agent_mesh.agent.utils.context_helpers import get_original_session_id

from .web_server import get_web_server

logger = logging.getLogger(__name__)


def _extract_artifact_references(html_content: str) -> List[str]:
    """
    Extract artifact filenames from SAM artifact references in HTML.

    Looks for patterns like: «artifact_content:filename >>> format:datauri»

    Args:
        html_content: HTML content as string

    Returns:
        List of artifact filenames referenced in the HTML
    """
    # Pattern to match «artifact_content:filename >>> format:datauri»
    pattern = r'«artifact_content:([^›»]+)\s*>>>'
    matches = re.findall(pattern, html_content)

    # Remove any whitespace and return unique filenames
    filenames = [match.strip() for match in matches]
    unique_filenames = list(dict.fromkeys(filenames))  # Preserve order while removing duplicates

    logger.debug(f"[ArtifactHost] Extracted {len(unique_filenames)} artifact references: {unique_filenames}")
    return unique_filenames


def _replace_artifact_references(html_content: str, filename_map: Dict[str, str]) -> str:
    """
    Replace SAM artifact references with normal relative URLs.

    Replaces: «artifact_content:filename >>> format:datauri»
    With: filename (or custom mapped name)

    Args:
        html_content: Original HTML content
        filename_map: Mapping of original filename to hosted filename

    Returns:
        Updated HTML content with artifact references replaced
    """
    def replace_reference(match):
        original_filename = match.group(1).strip()
        # Use mapped filename if available, otherwise use original
        hosted_filename = filename_map.get(original_filename, original_filename)
        return hosted_filename

    # Replace all artifact references
    pattern = r'«artifact_content:([^›»]+)\s*>>>[^»]*»'
    updated_html = re.sub(pattern, replace_reference, html_content)

    return updated_html


async def _host_single_artifact(
    artifact_filename: str,
    custom_filename: Optional[str],
    app_name: str,
    user_id: str,
    session_id: str,
    artifact_service: Any,
    web_server: Any,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Helper function to host a single artifact.

    Returns dict with 'status', 'hosted_filename', 'url', etc.
    """
    log_identifier = f"[ArtifactHost:_host_single:{artifact_filename}]"

    try:
        # Parse artifact filename and version
        parts = artifact_filename.rsplit(":", 1)
        filename_base = parts[0]
        version_str = parts[1] if len(parts) > 1 else None
        version_to_load = int(version_str) if version_str else None

        # Get latest version if not specified
        if version_to_load is None:
            list_versions_method = getattr(artifact_service, "list_versions")
            if inspect.iscoroutinefunction(list_versions_method):
                versions = await list_versions_method(
                    app_name=app_name, user_id=user_id, session_id=session_id, filename=filename_base
                )
            else:
                versions = await asyncio.to_thread(
                    list_versions_method, app_name=app_name, user_id=user_id,
                    session_id=session_id, filename=filename_base
                )
            if not versions:
                raise FileNotFoundError(f"Artifact '{filename_base}' not found.")
            version_to_load = max(versions)

        logger.debug(f"{log_identifier} Loading artifact version {version_to_load}")

        # Load artifact
        load_artifact_method = getattr(artifact_service, "load_artifact")
        if inspect.iscoroutinefunction(load_artifact_method):
            artifact = await load_artifact_method(
                app_name=app_name, user_id=user_id, session_id=session_id,
                filename=filename_base, version=version_to_load
            )
        else:
            artifact = await asyncio.to_thread(
                load_artifact_method, app_name=app_name, user_id=user_id,
                session_id=session_id, filename=filename_base, version=version_to_load
            )

        if not artifact or not artifact.inline_data:
            raise FileNotFoundError(f"Content for '{filename_base}' v{version_to_load} not found.")

        artifact_bytes = artifact.inline_data.data
        logger.debug(f"{log_identifier} Loaded artifact: {len(artifact_bytes)} bytes")

        # Determine hosted filename
        hosted_filename = custom_filename if custom_filename else filename_base

        # Ensure filename has extension
        if custom_filename and '.' not in custom_filename and '.' in filename_base:
            extension = Path(filename_base).suffix
            hosted_filename = f"{custom_filename}{extension}"

        # Write artifact to web server directory
        hosted_path = web_server.host_directory / hosted_filename
        await asyncio.to_thread(_write_file, hosted_path, artifact_bytes)

        logger.info(f"{log_identifier} Artifact written to {hosted_path}")

        # Generate URL
        url = web_server.get_url(hosted_filename, base_url)

        return {
            "status": "success",
            "artifact_filename": filename_base,
            "artifact_version": version_to_load,
            "hosted_filename": hosted_filename,
            "url": url,
        }

    except Exception as e:
        logger.error(f"{log_identifier} Failed to host: {e}")
        return {
            "status": "error",
            "artifact_filename": artifact_filename,
            "error": str(e)
        }


async def host_artifact(
    artifact_filename: str,
    custom_filename: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Host an artifact on the web server for easy access.

    Copies an artifact from the artifact service to the web server's hosting
    directory and returns a URL for accessing it.

    Args:
        artifact_filename: Artifact filename with optional version (e.g., "photo.jpg" or "photo.jpg:2")
        custom_filename: Optional custom name for the hosted file (default: use original name)
        tool_context: Framework context for accessing artifact service
        tool_config: Optional configuration:
            - base_url: Custom base URL for generated URLs (for firewall/proxy scenarios)

    Returns:
        Dictionary with status, message, hosted filename, and URL
    """
    log_identifier = f"[ArtifactHost:host_artifact:{artifact_filename}]"
    logger.info(f"{log_identifier} Hosting artifact")

    if not tool_context:
        logger.error(f"{log_identifier} ToolContext is missing.")
        return {"status": "error", "message": "ToolContext is required"}

    # Get web server instance
    web_server = get_web_server()
    if not web_server:
        logger.error(f"{log_identifier} Web server is not initialized")
        return {
            "status": "error",
            "message": "Web server is not running. Please check agent configuration."
        }

    try:
        # Extract invocation context
        inv_context = tool_context._invocation_context
        if not inv_context:
            raise ValueError("InvocationContext is not available.")

        app_name = getattr(inv_context, "app_name", None)
        user_id = getattr(inv_context, "user_id", None)
        session_id = get_original_session_id(inv_context)
        artifact_service = getattr(inv_context, "artifact_service", None)

        if not all([app_name, user_id, session_id, artifact_service]):
            raise ValueError("Missing required context parts")

        # Parse artifact filename and version
        parts = artifact_filename.rsplit(":", 1)
        filename_base = parts[0]
        version_str = parts[1] if len(parts) > 1 else None
        version_to_load = int(version_str) if version_str else None

        # Get latest version if not specified
        if version_to_load is None:
            list_versions_method = getattr(artifact_service, "list_versions")
            if inspect.iscoroutinefunction(list_versions_method):
                versions = await list_versions_method(
                    app_name=app_name, user_id=user_id, session_id=session_id, filename=filename_base
                )
            else:
                versions = await asyncio.to_thread(
                    list_versions_method, app_name=app_name, user_id=user_id,
                    session_id=session_id, filename=filename_base
                )
            if not versions:
                raise FileNotFoundError(f"Artifact '{filename_base}' not found.")
            version_to_load = max(versions)

        logger.debug(f"{log_identifier} Loading artifact version {version_to_load}")

        # Load artifact
        load_artifact_method = getattr(artifact_service, "load_artifact")
        if inspect.iscoroutinefunction(load_artifact_method):
            artifact = await load_artifact_method(
                app_name=app_name, user_id=user_id, session_id=session_id,
                filename=filename_base, version=version_to_load
            )
        else:
            artifact = await asyncio.to_thread(
                load_artifact_method, app_name=app_name, user_id=user_id,
                session_id=session_id, filename=filename_base, version=version_to_load
            )

        if not artifact or not artifact.inline_data:
            raise FileNotFoundError(f"Content for '{filename_base}' v{version_to_load} not found.")

        artifact_bytes = artifact.inline_data.data
        logger.debug(f"{log_identifier} Loaded artifact: {len(artifact_bytes)} bytes")

        # Determine hosted filename
        hosted_filename = custom_filename if custom_filename else filename_base

        # Ensure filename has extension
        if custom_filename and '.' not in custom_filename and '.' in filename_base:
            # Preserve original extension if custom name doesn't have one
            extension = Path(filename_base).suffix
            hosted_filename = f"{custom_filename}{extension}"

        # Get configuration
        current_tool_config = tool_config if tool_config is not None else {}
        base_url = current_tool_config.get("base_url")

        # Check if this is an HTML file - if so, process artifact references
        referenced_artifacts = []
        is_html = hosted_filename.lower().endswith(('.html', '.htm'))

        if is_html:
            try:
                # Decode HTML content
                html_content = artifact_bytes.decode('utf-8')

                # Extract artifact references
                referenced_filenames = _extract_artifact_references(html_content)

                if referenced_filenames:
                    logger.info(f"{log_identifier} Found {len(referenced_filenames)} artifact references in HTML: {referenced_filenames}")

                    # Host each referenced artifact
                    filename_map = {}
                    for ref_filename in referenced_filenames:
                        logger.info(f"{log_identifier} Hosting referenced artifact: {ref_filename}")
                        result = await _host_single_artifact(
                            artifact_filename=ref_filename,
                            custom_filename=None,
                            app_name=app_name,
                            user_id=user_id,
                            session_id=session_id,
                            artifact_service=artifact_service,
                            web_server=web_server,
                            base_url=base_url
                        )

                        if result["status"] == "success":
                            filename_map[ref_filename] = result["hosted_filename"]
                            referenced_artifacts.append({
                                "filename": ref_filename,
                                "hosted_filename": result["hosted_filename"],
                                "url": result["url"]
                            })
                            logger.info(f"{log_identifier} Successfully hosted {ref_filename} as {result['hosted_filename']}")
                        else:
                            logger.warning(f"{log_identifier} Failed to host {ref_filename}: {result.get('error')}")

                    # Replace artifact references in HTML with regular filenames
                    if filename_map:
                        updated_html = _replace_artifact_references(html_content, filename_map)
                        artifact_bytes = updated_html.encode('utf-8')
                        logger.info(f"{log_identifier} Replaced {len(filename_map)} artifact references in HTML")

            except UnicodeDecodeError:
                logger.warning(f"{log_identifier} Could not decode HTML content as UTF-8, skipping artifact reference processing")
            except Exception as e:
                logger.warning(f"{log_identifier} Error processing HTML artifact references: {e}")

        # Write artifact to web server directory
        hosted_path = web_server.host_directory / hosted_filename
        await asyncio.to_thread(_write_file, hosted_path, artifact_bytes)

        logger.info(f"{log_identifier} Artifact written to {hosted_path}")

        # Generate URL
        url = web_server.get_url(hosted_filename, base_url)

        logger.info(f"{log_identifier} Artifact hosted successfully at {url}")

        result = {
            "status": "success",
            "message": "Artifact hosted successfully",
            "artifact_filename": filename_base,
            "artifact_version": version_to_load,
            "hosted_filename": hosted_filename,
            "url": url,
        }

        # Add referenced artifacts info if any were processed
        if referenced_artifacts:
            result["referenced_artifacts"] = referenced_artifacts
            result["message"] = f"Artifact hosted successfully along with {len(referenced_artifacts)} referenced artifact(s)"

        return result

    except FileNotFoundError as e:
        logger.warning(f"{log_identifier} File not found: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"{log_identifier} Unexpected error: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}


def _write_file(path: Path, content: bytes) -> None:
    """
    Write content to a file (synchronous).

    Args:
        path: Path to write to
        content: Content bytes
    """
    with open(path, 'wb') as f:
        f.write(content)
