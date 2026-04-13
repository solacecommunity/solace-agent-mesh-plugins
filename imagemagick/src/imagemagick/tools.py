import logging
import asyncio
import inspect
import subprocess
import tempfile
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from pathlib import Path

from google.adk.tools import ToolContext
from solace_agent_mesh.agent.utils.artifact_helpers import (
    save_artifact_with_metadata,
    DEFAULT_SCHEMA_MAX_KEYS,
)
from solace_agent_mesh.agent.utils.context_helpers import get_original_session_id

logger = logging.getLogger(__name__)


async def crop_image(
    image_filename: str,
    width: int,
    height: int,
    x_offset: int = 0,
    y_offset: int = 0,
    output_filename: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Crop an image to specified dimensions using ImageMagick.

    Args:
        image_filename: Input image filename with optional version (e.g., "photo.jpg" or "photo.jpg:2")
        width: Width of the cropped area in pixels
        height: Height of the cropped area in pixels
        x_offset: X coordinate of the top-left corner (default: 0)
        y_offset: Y coordinate of the top-left corner (default: 0)
        output_filename: Optional output filename (default: adds "_cropped" suffix)
        tool_context: Framework context for accessing artifact service
        tool_config: Optional configuration

    Returns:
        Dictionary with status, message, and output file information
    """
    log_identifier = f"[ImageMagick:crop_image:{image_filename}]"
    logger.info(f"{log_identifier} Cropping to {width}x{height}+{x_offset}+{y_offset}")

    if not tool_context:
        logger.error(f"{log_identifier} ToolContext is missing.")
        return {"status": "error", "message": "ToolContext is missing."}

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

        # Parse input filename and version
        parts = image_filename.rsplit(":", 1)
        filename_base = parts[0]
        version_str = parts[1] if len(parts) > 1 else None
        version_to_load = int(version_str) if version_str else None

        # Get latest version if not specified
        if version_to_load is None:
            list_versions_method = getattr(artifact_service, "list_versions")
            if inspect.iscoroutinefunction(list_versions_method):
                versions = await list_versions_method(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id,
                    filename=filename_base,
                )
            else:
                versions = await asyncio.to_thread(
                    list_versions_method,
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id,
                    filename=filename_base,
                )
            if not versions:
                raise FileNotFoundError(f"Image artifact '{filename_base}' not found.")
            version_to_load = max(versions)

        # Load image artifact
        load_artifact_method = getattr(artifact_service, "load_artifact")
        if inspect.iscoroutinefunction(load_artifact_method):
            image_artifact = await load_artifact_method(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename_base,
                version=version_to_load,
            )
        else:
            image_artifact = await asyncio.to_thread(
                load_artifact_method,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename_base,
                version=version_to_load,
            )

        if not image_artifact or not image_artifact.inline_data:
            raise FileNotFoundError(f"Content for '{filename_base}' v{version_to_load} not found.")

        image_bytes = image_artifact.inline_data.data

        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename_base).suffix) as tmp_input:
            tmp_input.write(image_bytes)
            tmp_input_path = tmp_input.name

        try:
            # Determine output filename
            if not output_filename:
                name_parts = filename_base.rsplit(".", 1)
                if len(name_parts) == 2:
                    output_filename = f"{name_parts[0]}_cropped.{name_parts[1]}"
                else:
                    output_filename = f"{filename_base}_cropped"

            tmp_output_path = tempfile.mktemp(suffix=Path(output_filename).suffix)

            # Run ImageMagick crop command
            crop_geometry = f"{width}x{height}+{x_offset}+{y_offset}"
            cmd = ["convert", tmp_input_path, "-crop", crop_geometry, "+repage", tmp_output_path]

            logger.debug(f"{log_identifier} Running command: {' '.join(cmd)}")
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Read the output file
            with open(tmp_output_path, "rb") as f:
                output_bytes = f.read()

            # Determine MIME type
            suffix = Path(output_filename).suffix.lower()
            mime_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".bmp": "image/bmp",
                ".webp": "image/webp",
            }
            mime_type = mime_type_map.get(suffix, "application/octet-stream")

            # Save output artifact
            timestamp = datetime.now(timezone.utc)
            metadata_dict = {
                "description": f"Cropped image from {filename_base}",
                "source_tool": "crop_image",
                "source_filename": filename_base,
                "source_version": version_to_load,
                "crop_geometry": crop_geometry,
                "creation_timestamp_iso": timestamp.isoformat(),
            }

            save_result = await save_artifact_with_metadata(
                artifact_service=artifact_service,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=output_filename,
                content_bytes=output_bytes,
                mime_type=mime_type,
                metadata_dict=metadata_dict,
                timestamp=timestamp,
                schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
                tool_context=tool_context,
            )

            if save_result.get("status") == "error":
                raise Exception(f"Failed to save artifact: {save_result.get('message')}")

            logger.info(f"{log_identifier} Successfully cropped image to {output_filename}")
            return {
                "status": "success",
                "message": f"Image cropped successfully to {width}x{height}+{x_offset}+{y_offset}",
                "output_filename": output_filename,
                "output_version": save_result["data_version"],
                "crop_geometry": crop_geometry,
            }

        finally:
            # Clean up temporary files
            if os.path.exists(tmp_input_path):
                os.unlink(tmp_input_path)
            if os.path.exists(tmp_output_path):
                os.unlink(tmp_output_path)

    except subprocess.CalledProcessError as e:
        logger.error(f"{log_identifier} ImageMagick command failed: {e.stderr}")
        return {"status": "error", "message": f"ImageMagick error: {e.stderr}"}
    except FileNotFoundError as e:
        logger.warning(f"{log_identifier} File not found: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"{log_identifier} Unexpected error: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}


async def resize_image(
    image_filename: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    percentage: Optional[int] = None,
    maintain_aspect_ratio: bool = True,
    output_filename: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Resize an image using ImageMagick.

    Args:
        image_filename: Input image filename with optional version
        width: Target width in pixels (optional if percentage is used)
        height: Target height in pixels (optional if percentage is used)
        percentage: Resize by percentage (e.g., 50 for 50%)
        maintain_aspect_ratio: Keep aspect ratio when resizing (default: True)
        output_filename: Optional output filename (default: adds "_resized" suffix)
        tool_context: Framework context for accessing artifact service
        tool_config: Optional configuration

    Returns:
        Dictionary with status, message, and output file information
    """
    log_identifier = f"[ImageMagick:resize_image:{image_filename}]"
    logger.info(f"{log_identifier} Resizing image")

    if not tool_context:
        logger.error(f"{log_identifier} ToolContext is missing.")
        return {"status": "error", "message": "ToolContext is missing."}

    if not percentage and not width and not height:
        return {
            "status": "error",
            "message": "Must specify either percentage, width, or height"
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

        # Parse input filename and load image (same as crop_image)
        parts = image_filename.rsplit(":", 1)
        filename_base = parts[0]
        version_str = parts[1] if len(parts) > 1 else None
        version_to_load = int(version_str) if version_str else None

        if version_to_load is None:
            list_versions_method = getattr(artifact_service, "list_versions")
            if inspect.iscoroutinefunction(list_versions_method):
                versions = await list_versions_method(
                    app_name=app_name, user_id=user_id, session_id=session_id, filename=filename_base
                )
            else:
                versions = await asyncio.to_thread(
                    list_versions_method, app_name=app_name, user_id=user_id, session_id=session_id, filename=filename_base
                )
            if not versions:
                raise FileNotFoundError(f"Image artifact '{filename_base}' not found.")
            version_to_load = max(versions)

        load_artifact_method = getattr(artifact_service, "load_artifact")
        if inspect.iscoroutinefunction(load_artifact_method):
            image_artifact = await load_artifact_method(
                app_name=app_name, user_id=user_id, session_id=session_id,
                filename=filename_base, version=version_to_load
            )
        else:
            image_artifact = await asyncio.to_thread(
                load_artifact_method, app_name=app_name, user_id=user_id,
                session_id=session_id, filename=filename_base, version=version_to_load
            )

        if not image_artifact or not image_artifact.inline_data:
            raise FileNotFoundError(f"Content for '{filename_base}' v{version_to_load} not found.")

        image_bytes = image_artifact.inline_data.data

        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename_base).suffix) as tmp_input:
            tmp_input.write(image_bytes)
            tmp_input_path = tmp_input.name

        try:
            if not output_filename:
                name_parts = filename_base.rsplit(".", 1)
                if len(name_parts) == 2:
                    output_filename = f"{name_parts[0]}_resized.{name_parts[1]}"
                else:
                    output_filename = f"{filename_base}_resized"

            tmp_output_path = tempfile.mktemp(suffix=Path(output_filename).suffix)

            # Build resize geometry
            if percentage:
                resize_geometry = f"{percentage}%"
            elif width and height:
                if maintain_aspect_ratio:
                    resize_geometry = f"{width}x{height}"
                else:
                    resize_geometry = f"{width}x{height}!"
            elif width:
                resize_geometry = f"{width}x"
            else:  # height only
                resize_geometry = f"x{height}"

            # Run ImageMagick resize command
            cmd = ["convert", tmp_input_path, "-resize", resize_geometry, tmp_output_path]

            logger.debug(f"{log_identifier} Running command: {' '.join(cmd)}")
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, check=True
            )

            # Read output file
            with open(tmp_output_path, "rb") as f:
                output_bytes = f.read()

            # Determine MIME type
            suffix = Path(output_filename).suffix.lower()
            mime_type_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif", ".bmp": "image/bmp", ".webp": "image/webp",
            }
            mime_type = mime_type_map.get(suffix, "application/octet-stream")

            # Save output artifact
            timestamp = datetime.now(timezone.utc)
            metadata_dict = {
                "description": f"Resized image from {filename_base}",
                "source_tool": "resize_image",
                "source_filename": filename_base,
                "source_version": version_to_load,
                "resize_geometry": resize_geometry,
                "creation_timestamp_iso": timestamp.isoformat(),
            }

            save_result = await save_artifact_with_metadata(
                artifact_service=artifact_service,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=output_filename,
                content_bytes=output_bytes,
                mime_type=mime_type,
                metadata_dict=metadata_dict,
                timestamp=timestamp,
                schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
                tool_context=tool_context,
            )

            if save_result.get("status") == "error":
                raise Exception(f"Failed to save artifact: {save_result.get('message')}")

            logger.info(f"{log_identifier} Successfully resized image to {output_filename}")
            return {
                "status": "success",
                "message": f"Image resized successfully using geometry {resize_geometry}",
                "output_filename": output_filename,
                "output_version": save_result["data_version"],
                "resize_geometry": resize_geometry,
            }

        finally:
            if os.path.exists(tmp_input_path):
                os.unlink(tmp_input_path)
            if os.path.exists(tmp_output_path):
                os.unlink(tmp_output_path)

    except subprocess.CalledProcessError as e:
        logger.error(f"{log_identifier} ImageMagick command failed: {e.stderr}")
        return {"status": "error", "message": f"ImageMagick error: {e.stderr}"}
    except FileNotFoundError as e:
        logger.warning(f"{log_identifier} File not found: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"{log_identifier} Unexpected error: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}


async def convert_image_format(
    image_filename: str,
    output_format: str,
    output_filename: Optional[str] = None,
    quality: Optional[int] = None,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convert an image to a different format using ImageMagick.

    Args:
        image_filename: Input image filename with optional version
        output_format: Target format (e.g., "jpg", "png", "gif", "webp", "bmp")
        output_filename: Optional output filename (default: changes extension)
        quality: JPEG quality 1-100 (only for JPEG output)
        tool_context: Framework context for accessing artifact service
        tool_config: Optional configuration

    Returns:
        Dictionary with status, message, and output file information
    """
    log_identifier = f"[ImageMagick:convert_format:{image_filename}]"
    logger.info(f"{log_identifier} Converting to {output_format}")

    if not tool_context:
        logger.error(f"{log_identifier} ToolContext is missing.")
        return {"status": "error", "message": "ToolContext is missing."}

    # Validate format
    supported_formats = ["jpg", "jpeg", "png", "gif", "webp", "bmp"]
    output_format = output_format.lower()
    if output_format not in supported_formats:
        return {
            "status": "error",
            "message": f"Unsupported format '{output_format}'. Supported: {', '.join(supported_formats)}"
        }

    try:
        # Extract invocation context (same pattern as above)
        inv_context = tool_context._invocation_context
        if not inv_context:
            raise ValueError("InvocationContext is not available.")

        app_name = getattr(inv_context, "app_name", None)
        user_id = getattr(inv_context, "user_id", None)
        session_id = get_original_session_id(inv_context)
        artifact_service = getattr(inv_context, "artifact_service", None)

        if not all([app_name, user_id, session_id, artifact_service]):
            raise ValueError("Missing required context parts")

        # Load image artifact
        parts = image_filename.rsplit(":", 1)
        filename_base = parts[0]
        version_str = parts[1] if len(parts) > 1 else None
        version_to_load = int(version_str) if version_str else None

        if version_to_load is None:
            list_versions_method = getattr(artifact_service, "list_versions")
            if inspect.iscoroutinefunction(list_versions_method):
                versions = await list_versions_method(
                    app_name=app_name, user_id=user_id, session_id=session_id, filename=filename_base
                )
            else:
                versions = await asyncio.to_thread(
                    list_versions_method, app_name=app_name, user_id=user_id, session_id=session_id, filename=filename_base
                )
            if not versions:
                raise FileNotFoundError(f"Image artifact '{filename_base}' not found.")
            version_to_load = max(versions)

        load_artifact_method = getattr(artifact_service, "load_artifact")
        if inspect.iscoroutinefunction(load_artifact_method):
            image_artifact = await load_artifact_method(
                app_name=app_name, user_id=user_id, session_id=session_id,
                filename=filename_base, version=version_to_load
            )
        else:
            image_artifact = await asyncio.to_thread(
                load_artifact_method, app_name=app_name, user_id=user_id,
                session_id=session_id, filename=filename_base, version=version_to_load
            )

        if not image_artifact or not image_artifact.inline_data:
            raise FileNotFoundError(f"Content for '{filename_base}' v{version_to_load} not found.")

        image_bytes = image_artifact.inline_data.data

        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename_base).suffix) as tmp_input:
            tmp_input.write(image_bytes)
            tmp_input_path = tmp_input.name

        try:
            if not output_filename:
                name_base = filename_base.rsplit(".", 1)[0]
                output_filename = f"{name_base}.{output_format}"

            tmp_output_path = tempfile.mktemp(suffix=f".{output_format}")

            # Build ImageMagick command
            cmd = ["convert", tmp_input_path]

            # Add quality parameter for JPEG
            if quality and output_format in ["jpg", "jpeg"]:
                cmd.extend(["-quality", str(quality)])

            cmd.append(tmp_output_path)

            logger.debug(f"{log_identifier} Running command: {' '.join(cmd)}")
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, check=True
            )

            # Read output file
            with open(tmp_output_path, "rb") as f:
                output_bytes = f.read()

            # Determine MIME type
            mime_type_map = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "gif": "image/gif", "bmp": "image/bmp", "webp": "image/webp",
            }
            mime_type = mime_type_map.get(output_format, "application/octet-stream")

            # Save output artifact
            timestamp = datetime.now(timezone.utc)
            metadata_dict = {
                "description": f"Format converted image from {filename_base}",
                "source_tool": "convert_image_format",
                "source_filename": filename_base,
                "source_version": version_to_load,
                "output_format": output_format,
                "creation_timestamp_iso": timestamp.isoformat(),
            }
            if quality:
                metadata_dict["quality"] = quality

            save_result = await save_artifact_with_metadata(
                artifact_service=artifact_service,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=output_filename,
                content_bytes=output_bytes,
                mime_type=mime_type,
                metadata_dict=metadata_dict,
                timestamp=timestamp,
                schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
                tool_context=tool_context,
            )

            if save_result.get("status") == "error":
                raise Exception(f"Failed to save artifact: {save_result.get('message')}")

            logger.info(f"{log_identifier} Successfully converted image to {output_filename}")
            return {
                "status": "success",
                "message": f"Image converted successfully to {output_format}",
                "output_filename": output_filename,
                "output_version": save_result["data_version"],
                "output_format": output_format,
            }

        finally:
            if os.path.exists(tmp_input_path):
                os.unlink(tmp_input_path)
            if os.path.exists(tmp_output_path):
                os.unlink(tmp_output_path)

    except subprocess.CalledProcessError as e:
        logger.error(f"{log_identifier} ImageMagick command failed: {e.stderr}")
        return {"status": "error", "message": f"ImageMagick error: {e.stderr}"}
    except FileNotFoundError as e:
        logger.warning(f"{log_identifier} File not found: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"{log_identifier} Unexpected error: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}


async def add_text_overlay(
    image_filename: str,
    text: str,
    position: str = "south",
    font_size: int = 32,
    font_color: str = "white",
    background_color: Optional[str] = None,
    output_filename: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Add text overlay to an image using ImageMagick.

    Args:
        image_filename: Input image filename with optional version
        text: Text to overlay on the image
        position: Text position - north, south, east, west, center, northeast, northwest, southeast, southwest
        font_size: Font size in points (default: 32)
        font_color: Text color name or hex (e.g., "white", "#FF0000")
        background_color: Optional background color for text (e.g., "black", "#000000")
        output_filename: Optional output filename (default: adds "_text" suffix)
        tool_context: Framework context for accessing artifact service
        tool_config: Optional configuration

    Returns:
        Dictionary with status, message, and output file information
    """
    log_identifier = f"[ImageMagick:add_text:{image_filename}]"
    logger.info(f"{log_identifier} Adding text overlay: '{text}'")

    if not tool_context:
        logger.error(f"{log_identifier} ToolContext is missing.")
        return {"status": "error", "message": "ToolContext is missing."}

    # Validate position
    valid_positions = ["north", "south", "east", "west", "center", "northeast", "northwest", "southeast", "southwest"]
    position = position.lower()
    if position not in valid_positions:
        return {
            "status": "error",
            "message": f"Invalid position '{position}'. Valid: {', '.join(valid_positions)}"
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

        # Load image artifact
        parts = image_filename.rsplit(":", 1)
        filename_base = parts[0]
        version_str = parts[1] if len(parts) > 1 else None
        version_to_load = int(version_str) if version_str else None

        if version_to_load is None:
            list_versions_method = getattr(artifact_service, "list_versions")
            if inspect.iscoroutinefunction(list_versions_method):
                versions = await list_versions_method(
                    app_name=app_name, user_id=user_id, session_id=session_id, filename=filename_base
                )
            else:
                versions = await asyncio.to_thread(
                    list_versions_method, app_name=app_name, user_id=user_id, session_id=session_id, filename=filename_base
                )
            if not versions:
                raise FileNotFoundError(f"Image artifact '{filename_base}' not found.")
            version_to_load = max(versions)

        load_artifact_method = getattr(artifact_service, "load_artifact")
        if inspect.iscoroutinefunction(load_artifact_method):
            image_artifact = await load_artifact_method(
                app_name=app_name, user_id=user_id, session_id=session_id,
                filename=filename_base, version=version_to_load
            )
        else:
            image_artifact = await asyncio.to_thread(
                load_artifact_method, app_name=app_name, user_id=user_id,
                session_id=session_id, filename=filename_base, version=version_to_load
            )

        if not image_artifact or not image_artifact.inline_data:
            raise FileNotFoundError(f"Content for '{filename_base}' v{version_to_load} not found.")

        image_bytes = image_artifact.inline_data.data

        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename_base).suffix) as tmp_input:
            tmp_input.write(image_bytes)
            tmp_input_path = tmp_input.name

        try:
            if not output_filename:
                name_parts = filename_base.rsplit(".", 1)
                if len(name_parts) == 2:
                    output_filename = f"{name_parts[0]}_text.{name_parts[1]}"
                else:
                    output_filename = f"{filename_base}_text"

            tmp_output_path = tempfile.mktemp(suffix=Path(output_filename).suffix)

            # Build ImageMagick command
            cmd = ["convert", tmp_input_path]

            # Add background color if specified
            if background_color:
                cmd.extend([
                    "-background", background_color,
                    "-fill", font_color,
                    "-pointsize", str(font_size),
                    "-gravity", position,
                    "-annotate", "+0+0", text
                ])
            else:
                cmd.extend([
                    "-fill", font_color,
                    "-pointsize", str(font_size),
                    "-gravity", position,
                    "-annotate", "+0+0", text
                ])

            cmd.append(tmp_output_path)

            logger.debug(f"{log_identifier} Running command: {' '.join(cmd)}")
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, check=True
            )

            # Read output file
            with open(tmp_output_path, "rb") as f:
                output_bytes = f.read()

            # Determine MIME type
            suffix = Path(output_filename).suffix.lower()
            mime_type_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif", ".bmp": "image/bmp", ".webp": "image/webp",
            }
            mime_type = mime_type_map.get(suffix, "application/octet-stream")

            # Save output artifact
            timestamp = datetime.now(timezone.utc)
            metadata_dict = {
                "description": f"Text overlay added to {filename_base}",
                "source_tool": "add_text_overlay",
                "source_filename": filename_base,
                "source_version": version_to_load,
                "overlay_text": text,
                "text_position": position,
                "font_size": font_size,
                "font_color": font_color,
                "creation_timestamp_iso": timestamp.isoformat(),
            }
            if background_color:
                metadata_dict["background_color"] = background_color

            save_result = await save_artifact_with_metadata(
                artifact_service=artifact_service,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=output_filename,
                content_bytes=output_bytes,
                mime_type=mime_type,
                metadata_dict=metadata_dict,
                timestamp=timestamp,
                schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
                tool_context=tool_context,
            )

            if save_result.get("status") == "error":
                raise Exception(f"Failed to save artifact: {save_result.get('message')}")

            logger.info(f"{log_identifier} Successfully added text overlay to {output_filename}")
            return {
                "status": "success",
                "message": f"Text overlay added successfully",
                "output_filename": output_filename,
                "output_version": save_result["data_version"],
                "text": text,
                "position": position,
            }

        finally:
            if os.path.exists(tmp_input_path):
                os.unlink(tmp_input_path)
            if os.path.exists(tmp_output_path):
                os.unlink(tmp_output_path)

    except subprocess.CalledProcessError as e:
        logger.error(f"{log_identifier} ImageMagick command failed: {e.stderr}")
        return {"status": "error", "message": f"ImageMagick error: {e.stderr}"}
    except FileNotFoundError as e:
        logger.warning(f"{log_identifier} File not found: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"{log_identifier} Unexpected error: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}


async def get_image_info(
    image_filename: str,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get detailed information about an image using ImageMagick.

    Returns image metadata including dimensions, format, file size, color space,
    bit depth, and compression type.

    Args:
        image_filename: Input image filename with optional version (e.g., "photo.jpg" or "photo.jpg:2")
        tool_context: Framework context for accessing artifact service
        tool_config: Optional configuration

    Returns:
        Dictionary with status, message, and image information
    """
    log_identifier = f"[ImageMagick:get_image_info:{image_filename}]"
    logger.info(f"{log_identifier} Getting image information")

    if not tool_context:
        logger.error(f"{log_identifier} ToolContext is missing.")
        return {"status": "error", "message": "ToolContext is missing."}

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

        # Parse input filename and version
        parts = image_filename.rsplit(":", 1)
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
                raise FileNotFoundError(f"Image artifact '{filename_base}' not found.")
            version_to_load = max(versions)

        # Load image artifact
        load_artifact_method = getattr(artifact_service, "load_artifact")
        if inspect.iscoroutinefunction(load_artifact_method):
            image_artifact = await load_artifact_method(
                app_name=app_name, user_id=user_id, session_id=session_id,
                filename=filename_base, version=version_to_load
            )
        else:
            image_artifact = await asyncio.to_thread(
                load_artifact_method, app_name=app_name, user_id=user_id,
                session_id=session_id, filename=filename_base, version=version_to_load
            )

        if not image_artifact or not image_artifact.inline_data:
            raise FileNotFoundError(f"Content for '{filename_base}' v{version_to_load} not found.")

        image_bytes = image_artifact.inline_data.data

        # Create temporary file for the image
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename_base).suffix) as tmp_input:
            tmp_input.write(image_bytes)
            tmp_input_path = tmp_input.name

        try:
            # Run ImageMagick identify command with detailed format
            cmd = [
                "identify",
                "-format",
                "%w|%h|%m|%b|%[colorspace]|%z|%C|%Q",
                tmp_input_path
            ]

            logger.debug(f"{log_identifier} Running command: {' '.join(cmd)}")
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Parse the output
            # Format: width|height|format|filesize|colorspace|depth|compression|quality
            output = result.stdout.strip()
            parts_output = output.split('|')

            if len(parts_output) >= 7:
                width = int(parts_output[0])
                height = int(parts_output[1])
                image_format = parts_output[2]
                file_size = parts_output[3]
                colorspace = parts_output[4]
                bit_depth = int(parts_output[5]) if parts_output[5].isdigit() else None
                compression = parts_output[6]
                quality = int(parts_output[7]) if len(parts_output) > 7 and parts_output[7].isdigit() else None

                logger.info(f"{log_identifier} Image info retrieved: {width}x{height} {image_format}")

                result_dict = {
                    "status": "success",
                    "message": "Image information retrieved successfully",
                    "filename": filename_base,
                    "version": version_to_load,
                    "format": image_format,
                    "dimensions": {
                        "width": width,
                        "height": height
                    },
                    "file_size": file_size,
                    "file_size_bytes": len(image_bytes),
                    "colorspace": colorspace,
                    "compression": compression,
                }

                if bit_depth is not None:
                    result_dict["bit_depth"] = bit_depth
                if quality is not None:
                    result_dict["quality"] = quality

                return result_dict
            else:
                raise Exception(f"Unexpected identify output format: {output}")

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_input_path):
                os.unlink(tmp_input_path)

    except subprocess.CalledProcessError as e:
        logger.error(f"{log_identifier} ImageMagick identify command failed: {e.stderr}")
        return {"status": "error", "message": f"ImageMagick error: {e.stderr}"}
    except FileNotFoundError as e:
        logger.warning(f"{log_identifier} File not found: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"{log_identifier} Unexpected error: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}
