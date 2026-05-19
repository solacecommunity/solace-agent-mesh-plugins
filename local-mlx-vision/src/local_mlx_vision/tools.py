import logging
import asyncio
import subprocess
import tempfile
import platform
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from google.adk.tools import ToolContext
from solace_agent_mesh.agent.utils.artifact_helpers import (
    save_artifact_with_metadata,
    DEFAULT_SCHEMA_MAX_KEYS,
)
from solace_agent_mesh.agent.utils.context_helpers import get_original_session_id

log = logging.getLogger(__name__)

PLUGIN_NAME = "local-mlx-vision"


def validate_apple_silicon() -> Dict[str, Any]:
    """
    Validate that the current platform is macOS with Apple Silicon.

    Returns:
        Dict containing validation status and error message if applicable.
    """
    log_identifier = f"[{PLUGIN_NAME}:validate_apple_silicon]"

    # Check if macOS
    if platform.system() != "Darwin":
        error_msg = f"mlx-vlm requires macOS. Current platform: {platform.system()}"
        log.error(f"{log_identifier} {error_msg}")
        return {
            "valid": False,
            "error": error_msg
        }

    # Check if Apple Silicon (arm64)
    if platform.machine() != "arm64":
        error_msg = f"mlx-vlm requires Apple Silicon (arm64). Current architecture: {platform.machine()}"
        log.warning(f"{log_identifier} {error_msg}")
        return {
            "valid": False,
            "error": error_msg
        }

    log.info(f"{log_identifier} Platform validation passed: macOS on Apple Silicon")
    return {"valid": True}


async def analyze_image(
    prompt: str,
    image_path: Optional[str] = None,
    image_artifact: Optional[str] = None,
    system_message: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.0,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyze an image using the local MLX vision model (Qwen3-VL-2B-Instruct-4bit).

    This tool uses mlx-vlm to run vision model inference locally on Apple Silicon.
    You can provide either a direct file path or a SAM artifact reference.

    Args:
        prompt: The question or instruction for the vision model (e.g., "Describe this image",
                "OCR this receipt and provide fields in JSON format", "What objects are in this image?")
        image_path: Direct file path to the image on disk (optional if image_artifact is provided)
        image_artifact: SAM artifact reference in format "filename:version" or just "filename" for latest
                       (optional if image_path is provided)
        system_message: Optional system message to guide the model's behavior
        max_tokens: Maximum number of tokens to generate (default: 4000)
        temperature: Sampling temperature for generation (default: 0.0 for deterministic output)

    Returns:
        Dict containing:
            - status: "success" or "error"
            - response: The model's text response (if successful)
            - model: The model used
            - prompt_used: The prompt that was sent
            - image_source: Information about which image was processed
            - error: Error message (if failed)

    Examples:
        - OCR a receipt: analyze_image(prompt="OCR this receipt and extract all fields as JSON", image_path="receipt.png")
        - Describe image: analyze_image(prompt="Describe what is happening in this image in detail", image_artifact="photo.jpg:1")
        - Identify objects: analyze_image(prompt="List all objects visible in this image", image_path="/path/to/image.jpg")
    """
    log_identifier = f"[{PLUGIN_NAME}:analyze_image]"
    log.info(f"{log_identifier} Starting image analysis with prompt: '{prompt[:100]}...'")

    # Validate platform
    platform_check = validate_apple_silicon()
    if not platform_check["valid"]:
        return {
            "status": "error",
            "error": platform_check["error"],
            "message": "Platform validation failed. This tool requires macOS on Apple Silicon."
        }

    # Validate that at least one image source is provided
    if not image_path and not image_artifact:
        error_msg = "Either image_path or image_artifact must be provided"
        log.error(f"{log_identifier} {error_msg}")
        return {
            "status": "error",
            "error": error_msg,
            "message": "Please provide either image_path or image_artifact parameter."
        }

    # Handle artifact if provided
    temp_file_path = None
    image_source_info = {}

    if image_artifact:
        log.info(f"{log_identifier} Processing image artifact: {image_artifact}")

        if not tool_context or not tool_context._invocation_context:
            error_msg = "ToolContext is required to load artifacts"
            log.error(f"{log_identifier} {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "message": "Cannot load artifact without proper context."
            }

        inv_context = tool_context._invocation_context
        artifact_service = getattr(inv_context, "artifact_service", None)
        app_name = getattr(inv_context, "app_name", None)
        user_id = getattr(inv_context, "user_id", None)
        session_id = get_original_session_id(inv_context)

        if not all([artifact_service, app_name, user_id, session_id]):
            error_msg = "Missing required context for artifact loading"
            log.error(f"{log_identifier} {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "message": "Cannot load artifact without proper context."
            }

        # Parse artifact reference (format: "filename:version" or just "filename")
        artifact_parts = image_artifact.split(":")
        artifact_filename = artifact_parts[0]
        artifact_version = int(artifact_parts[1]) if len(artifact_parts) > 1 else None

        try:
            # Try async method first, fall back to sync if not available
            if hasattr(artifact_service, "load_artifact"):
                if asyncio.iscoroutinefunction(artifact_service.load_artifact):
                    artifact_part = await artifact_service.load_artifact(
                        app_name=app_name,
                        user_id=user_id,
                        session_id=session_id,
                        filename=artifact_filename,
                        version=artifact_version,
                    )
                else:
                    artifact_part = artifact_service.load_artifact(
                        app_name=app_name,
                        user_id=user_id,
                        session_id=session_id,
                        filename=artifact_filename,
                        version=artifact_version,
                    )
            else:
                error_msg = "artifact_service does not have load_artifact method"
                log.error(f"{log_identifier} {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg
                }

            # Extract bytes from artifact - handle different return types
            # The artifact service can return different types depending on version:
            # - Part with inline_data.data (Google A2A format)
            # - Part with file.bytes (A2A FilePart format)
            # - Direct bytes
            # - Tuple with Part as first element
            artifact_data = None

            log.debug(f"{log_identifier} Artifact part type: {type(artifact_part)}, attrs: {dir(artifact_part) if artifact_part else 'None'}")

            if isinstance(artifact_part, bytes):
                # Direct bytes
                artifact_data = artifact_part
            elif hasattr(artifact_part, 'inline_data') and artifact_part.inline_data is not None:
                # Part object with inline_data (Google format)
                if hasattr(artifact_part.inline_data, 'data'):
                    artifact_data = artifact_part.inline_data.data
                elif hasattr(artifact_part.inline_data, 'blob'):
                    artifact_data = artifact_part.inline_data.blob
            elif hasattr(artifact_part, 'file') and artifact_part.file is not None:
                # A2A FilePart format
                if hasattr(artifact_part.file, 'bytes'):
                    artifact_data = artifact_part.file.bytes
                elif hasattr(artifact_part.file, 'content_bytes'):
                    artifact_data = artifact_part.file.content_bytes
            elif hasattr(artifact_part, 'content_bytes'):
                # SamFilePart format
                artifact_data = artifact_part.content_bytes
            elif hasattr(artifact_part, 'data'):
                # Object with direct data attribute
                artifact_data = artifact_part.data
            elif isinstance(artifact_part, tuple) and len(artifact_part) >= 1:
                # Tuple - recursively extract from first element
                first_elem = artifact_part[0]
                if isinstance(first_elem, bytes):
                    artifact_data = first_elem
                elif hasattr(first_elem, 'inline_data') and first_elem.inline_data and hasattr(first_elem.inline_data, 'data'):
                    artifact_data = first_elem.inline_data.data
                elif hasattr(first_elem, 'file') and first_elem.file and hasattr(first_elem.file, 'bytes'):
                    artifact_data = first_elem.file.bytes

            if artifact_data is None:
                error_msg = f"Could not extract data from artifact. Type: {type(artifact_part)}"
                log.error(f"{log_identifier} {error_msg}")
                # Log more details for debugging
                if artifact_part is not None:
                    log.error(f"{log_identifier} Artifact attributes: {[a for a in dir(artifact_part) if not a.startswith('_')]}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "message": "Could not extract data from artifact. Please check logs for details."
                }

            # Ensure we have bytes
            if not isinstance(artifact_data, bytes):
                error_msg = f"Artifact data is not bytes: {type(artifact_data)}"
                log.error(f"{log_identifier} {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "message": "Could not extract bytes from artifact."
                }

            log.debug(f"{log_identifier} Extracted {len(artifact_data)} bytes from artifact")

            # Save artifact to temporary file
            suffix = Path(artifact_filename).suffix or ".png"
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(artifact_data)
                temp_file_path = tmp_file.name

            actual_image_path = temp_file_path
            image_source_info = {
                "source": "artifact",
                "artifact_name": artifact_filename,
                "artifact_version": artifact_version,
                "temp_path": temp_file_path
            }
            log.info(f"{log_identifier} Loaded artifact to temporary file: {temp_file_path}")

        except Exception as e:
            error_msg = f"Failed to load artifact: {str(e)}"
            log.exception(f"{log_identifier} {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "message": "Could not load the specified artifact."
            }
    else:
        # Use provided file path
        actual_image_path = image_path
        image_source_info = {
            "source": "file_path",
            "path": image_path
        }
        log.info(f"{log_identifier} Using direct file path: {image_path}")

    # Verify image file exists
    if not os.path.exists(actual_image_path):
        error_msg = f"Image file not found: {actual_image_path}"
        log.error(f"{log_identifier} {error_msg}")
        # Clean up temp file if we created one
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return {
            "status": "error",
            "error": error_msg,
            "message": "The specified image file does not exist."
        }

    # Get model from config (default to Qwen3-VL-2B-Instruct-4bit)
    current_tool_config = tool_config if tool_config is not None else {}
    model = current_tool_config.get("model", "mlx-community/Qwen3-VL-2B-Instruct-4bit")

    # Build the mlx-vlm command
    cmd = [
        "python", "-m", "mlx_vlm.generate",
        "--model", model,
        "--max-tokens", str(max_tokens),
        "--temperature", str(temperature),
        "--prompt", prompt,
        "--image", actual_image_path
    ]

    # Add system message if provided
    if system_message:
        cmd.extend(["--system", system_message])

    log.info(f"{log_identifier} Executing mlx-vlm command: {' '.join(cmd)}")

    try:
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Clean up temp file if we created one
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            log.info(f"{log_identifier} Cleaned up temporary file: {temp_file_path}")

        if result.returncode != 0:
            error_msg = f"mlx-vlm command failed with exit code {result.returncode}"
            log.error(f"{log_identifier} {error_msg}")
            log.error(f"{log_identifier} stderr: {result.stderr}")
            return {
                "status": "error",
                "error": error_msg,
                "stderr": result.stderr,
                "message": "Vision model execution failed."
            }

        # Parse the output
        output = result.stdout.strip()
        log.info(f"{log_identifier} Successfully received model response ({len(output)} characters)")

        return {
            "status": "success",
            "response": output,
            "model": model,
            "prompt_used": prompt,
            "system_message": system_message,
            "image_source": image_source_info,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "message": "Image analyzed successfully."
        }

    except subprocess.TimeoutExpired:
        error_msg = "mlx-vlm command timed out after 5 minutes"
        log.error(f"{log_identifier} {error_msg}")
        # Clean up temp file if we created one
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return {
            "status": "error",
            "error": error_msg,
            "message": "Vision model execution timed out."
        }
    except Exception as e:
        error_msg = f"Unexpected error during image analysis: {str(e)}"
        log.exception(f"{log_identifier} {error_msg}")
        # Clean up temp file if we created one
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return {
            "status": "error",
            "error": error_msg,
            "message": "An unexpected error occurred during image analysis."
        }


# Standalone testing
if __name__ == "__main__":
    async def run_tests():
        print("--- Testing validate_apple_silicon ---")
        validation_result = validate_apple_silicon()
        print(f"Platform validation: {validation_result}")

        if validation_result["valid"]:
            print("\n--- Testing analyze_image with file path ---")
            # Note: This requires a test image and mlx-vlm to be installed
            test_image = "test.png"
            if os.path.exists(test_image):
                result = await analyze_image(
                    prompt="Describe this image in detail.",
                    image_path=test_image,
                    tool_context=None
                )
                print(f"Analysis result: {result}")
            else:
                print(f"Test image '{test_image}' not found, skipping analysis test")
        else:
            print("Skipping analyze_image test - platform validation failed")

    asyncio.run(run_tests())
