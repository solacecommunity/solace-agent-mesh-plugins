import logging
import os
import tempfile
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from google.adk.tools import ToolContext
from solace_agent_mesh.agent.utils.artifact_helpers import (
    save_artifact_with_metadata,
    DEFAULT_SCHEMA_MAX_KEYS,
)
from solace_agent_mesh.agent.utils.context_helpers import get_original_session_id

log = logging.getLogger(__name__)

# Supported formats
VIDEO_FORMATS = ["mp4", "mkv", "avi", "webm", "mov", "flv"]
AUDIO_FORMATS = ["mp3", "wav", "aac", "flac", "ogg", "m4a"]

# Quality presets for encoding
VIDEO_QUALITY_PRESETS = {
    "high": {"crf": "18", "preset": "slow"},
    "medium": {"crf": "23", "preset": "medium"},
    "low": {"crf": "28", "preset": "fast"}
}


async def _load_artifact_as_temp_file(
    artifact_service,
    app_name: str,
    user_id: str,
    session_id: str,
    artifact_filename: str,
    temp_dir: str
) -> str:
    """
    Load an artifact from the artifact service and save it as a temporary file.

    Returns:
        Path to the temporary file
    """
    log_id = "[VideoEditorTools:_load_artifact]"

    try:
        # Load the artifact using the correct API
        artifact = await artifact_service.load_artifact(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=artifact_filename
        )

        # Extract the bytes content from the artifact
        # The artifact object has inline_data.data containing the bytes
        if hasattr(artifact, 'inline_data') and hasattr(artifact.inline_data, 'data'):
            content = artifact.inline_data.data
        else:
            raise ValueError(f"Artifact does not have expected inline_data.data structure")

        # Determine file extension from original filename
        _, ext = os.path.splitext(artifact_filename)

        # Save to temporary file
        temp_file_path = os.path.join(temp_dir, f"input{ext}")

        with open(temp_file_path, 'wb') as f:
            f.write(content)

        log.info(f"{log_id} Loaded artifact '{artifact_filename}' to {temp_file_path}")
        return temp_file_path

    except Exception as e:
        log.error(f"{log_id} Failed to load artifact: {e}")
        raise


async def convert_video_format(
    input_artifact: str,
    output_format: str,
    quality: str = "medium",
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convert a video file to a different format.

    Args:
        input_artifact: Name of the input video artifact
        output_format: Target format (mp4, mkv, avi, webm, mov, flv)
        quality: Encoding quality preset (high, medium, low). Default: medium

    Returns:
        A dictionary with status, message, and output artifact information
    """
    plugin_name = "video-editor-tools"
    log_identifier = f"[{plugin_name}:convert_video_format]"
    log.info(f"{log_identifier} Converting '{input_artifact}' to {output_format}")

    # Validate format
    if output_format.lower() not in VIDEO_FORMATS:
        return {
            "status": "error",
            "message": f"Invalid format '{output_format}'. Supported: {', '.join(VIDEO_FORMATS)}"
        }

    # Validate quality
    if quality not in VIDEO_QUALITY_PRESETS:
        log.warning(f"{log_identifier} Invalid quality '{quality}', using 'medium'")
        quality = "medium"

    # Validate tool context
    if not tool_context or not tool_context._invocation_context:
        log.error(f"{log_identifier} ToolContext or InvocationContext is missing.")
        return {
            "status": "error",
            "message": "ToolContext or InvocationContext is missing.",
        }

    inv_context = tool_context._invocation_context
    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        return {
            "status": "error",
            "message": "Missing required context parts for artifact operations",
        }

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="video_convert_")
    temp_input = None
    temp_output = None

    try:
        # Load input video from artifact
        temp_input = await _load_artifact_as_temp_file(
            artifact_service, app_name, user_id, session_id,
            input_artifact, temp_dir
        )

        # Prepare output path
        temp_output = os.path.join(temp_dir, f"output.{output_format}")

        # Get quality settings
        settings = VIDEO_QUALITY_PRESETS[quality]

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i", temp_input,
            "-c:v", "libx264",
            "-crf", settings["crf"],
            "-preset", settings["preset"],
            "-c:a", "aac",
            "-b:a", "192k",
            "-y",  # Overwrite output file
            temp_output
        ]

        log.info(f"{log_identifier} Running ffmpeg conversion")

        # Run ffmpeg
        timeout = tool_config.get("timeout_seconds", 600) if tool_config else 600
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} FFmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"Video conversion failed: {result.stderr[:300]}"
            }

        log.info(f"{log_identifier} Conversion completed successfully")

        # Read output file
        with open(temp_output, 'rb') as f:
            output_content = f.read()

        # Generate output filename
        timestamp = datetime.now(timezone.utc)
        input_base = os.path.splitext(input_artifact)[0]
        output_filename = f"{input_base}_converted.{output_format}"

        # Save as artifact
        metadata_dict = {
            "description": f"Video converted from {input_artifact} to {output_format}",
            "source_tool": "convert_video_format",
            "input_artifact": input_artifact,
            "output_format": output_format,
            "quality": quality,
            "creation_timestamp_iso": timestamp.isoformat(),
        }

        log.info(f"{log_identifier} Saving output artifact: {output_filename}")

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=output_content,
            mime_type=f"video/{output_format}",
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )

        if save_result.get("status") == "error":
            log.error(f"{log_identifier} Failed to save artifact: {save_result.get('message')}")
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        log.info(f"{log_identifier} Artifact saved successfully")

        return {
            "status": "success",
            "message": f"Successfully converted video to {output_format}",
            "output_artifact": output_filename,
            "output_version": save_result["data_version"],
            "file_size_bytes": len(output_content),
            "quality": quality,
        }

    except subprocess.TimeoutExpired:
        log.error(f"{log_identifier} Conversion timed out")
        return {
            "status": "error",
            "message": f"Video conversion timed out after {timeout} seconds"
        }
    except FileNotFoundError as e:
        log.error(f"{log_identifier} Artifact not found: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during conversion: {str(e)}"
        }
    finally:
        # Cleanup temporary files
        try:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
            log.info(f"{log_identifier} Cleaned up temporary files")
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up: {e}")


async def trim_video(
    input_artifact: str,
    start_time: float,
    end_time: float,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Trim a video to a specific time range.

    Args:
        input_artifact: Name of the input video artifact
        start_time: Start time in seconds (e.g., 10.5 for 10.5 seconds)
        end_time: End time in seconds (e.g., 60.0 for 1 minute)

    Returns:
        A dictionary with status, message, and output artifact information
    """
    plugin_name = "video-editor-tools"
    log_identifier = f"[{plugin_name}:trim_video]"
    log.info(f"{log_identifier} Trimming '{input_artifact}' from {start_time}s to {end_time}s")

    # Validate times
    if start_time < 0 or end_time <= start_time:
        return {
            "status": "error",
            "message": "Invalid time range. end_time must be greater than start_time, and both must be positive."
        }

    # Validate tool context
    if not tool_context or not tool_context._invocation_context:
        return {
            "status": "error",
            "message": "ToolContext or InvocationContext is missing.",
        }

    inv_context = tool_context._invocation_context
    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        return {
            "status": "error",
            "message": "Missing required context parts for artifact operations",
        }

    temp_dir = tempfile.mkdtemp(prefix="video_trim_")
    temp_input = None
    temp_output = None

    try:
        # Load input video
        temp_input = await _load_artifact_as_temp_file(
            artifact_service, app_name, user_id, session_id,
            input_artifact, temp_dir
        )

        # Prepare output path
        input_ext = os.path.splitext(input_artifact)[1]
        temp_output = os.path.join(temp_dir, f"output{input_ext}")

        # Calculate duration
        duration = end_time - start_time

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i", temp_input,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c", "copy",  # Copy codec without re-encoding for speed
            "-y",
            temp_output
        ]

        log.info(f"{log_identifier} Running ffmpeg trim")

        # Run ffmpeg
        timeout = tool_config.get("timeout_seconds", 600) if tool_config else 600
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} FFmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"Video trim failed: {result.stderr[:300]}"
            }

        log.info(f"{log_identifier} Trim completed successfully")

        # Read output file
        with open(temp_output, 'rb') as f:
            output_content = f.read()

        # Generate output filename
        timestamp = datetime.now(timezone.utc)
        input_base = os.path.splitext(input_artifact)[0]
        output_filename = f"{input_base}_trimmed_{int(start_time)}-{int(end_time)}s{input_ext}"

        # Save as artifact
        metadata_dict = {
            "description": f"Video trimmed from {start_time}s to {end_time}s",
            "source_tool": "trim_video",
            "input_artifact": input_artifact,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "creation_timestamp_iso": timestamp.isoformat(),
        }

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=output_content,
            mime_type=f"video/{input_ext.lstrip('.')}",
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )

        if save_result.get("status") == "error":
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        return {
            "status": "success",
            "message": f"Successfully trimmed video from {start_time}s to {end_time}s",
            "output_artifact": output_filename,
            "output_version": save_result["data_version"],
            "file_size_bytes": len(output_content),
            "duration_seconds": duration,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Video trim timed out after {timeout} seconds"
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during trim: {str(e)}"
        }
    finally:
        try:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up: {e}")


async def extract_audio(
    input_artifact: str,
    output_format: str = "mp3",
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Extract audio from a video file.

    Args:
        input_artifact: Name of the input video artifact
        output_format: Audio format (mp3, wav, aac, flac, ogg, m4a). Default: mp3

    Returns:
        A dictionary with status, message, and output artifact information
    """
    plugin_name = "video-editor-tools"
    log_identifier = f"[{plugin_name}:extract_audio]"
    log.info(f"{log_identifier} Extracting audio from '{input_artifact}' as {output_format}")

    # Validate format
    if output_format.lower() not in AUDIO_FORMATS:
        return {
            "status": "error",
            "message": f"Invalid format '{output_format}'. Supported: {', '.join(AUDIO_FORMATS)}"
        }

    # Validate tool context
    if not tool_context or not tool_context._invocation_context:
        return {
            "status": "error",
            "message": "ToolContext or InvocationContext is missing.",
        }

    inv_context = tool_context._invocation_context
    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        return {
            "status": "error",
            "message": "Missing required context parts for artifact operations",
        }

    temp_dir = tempfile.mkdtemp(prefix="audio_extract_")
    temp_input = None
    temp_output = None

    try:
        # Load input video
        temp_input = await _load_artifact_as_temp_file(
            artifact_service, app_name, user_id, session_id,
            input_artifact, temp_dir
        )

        # Prepare output path
        temp_output = os.path.join(temp_dir, f"output.{output_format}")

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i", temp_input,
            "-vn",  # No video
            "-acodec", "libmp3lame" if output_format == "mp3" else "copy",
            "-q:a", "2",  # Good quality
            "-y",
            temp_output
        ]

        log.info(f"{log_identifier} Running ffmpeg audio extraction")

        # Run ffmpeg
        timeout = tool_config.get("timeout_seconds", 300) if tool_config else 300
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} FFmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"Audio extraction failed: {result.stderr[:300]}"
            }

        log.info(f"{log_identifier} Audio extraction completed successfully")

        # Read output file
        with open(temp_output, 'rb') as f:
            output_content = f.read()

        # Generate output filename
        timestamp = datetime.now(timezone.utc)
        input_base = os.path.splitext(input_artifact)[0]
        output_filename = f"{input_base}_audio.{output_format}"

        # Save as artifact
        metadata_dict = {
            "description": f"Audio extracted from {input_artifact}",
            "source_tool": "extract_audio",
            "input_artifact": input_artifact,
            "output_format": output_format,
            "creation_timestamp_iso": timestamp.isoformat(),
        }

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=output_content,
            mime_type=f"audio/{output_format}",
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )

        if save_result.get("status") == "error":
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        return {
            "status": "success",
            "message": f"Successfully extracted audio as {output_format}",
            "output_artifact": output_filename,
            "output_version": save_result["data_version"],
            "file_size_bytes": len(output_content),
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Audio extraction timed out after {timeout} seconds"
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during audio extraction: {str(e)}"
        }
    finally:
        try:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up: {e}")


async def compress_video(
    input_artifact: str,
    target_size_mb: Optional[float] = None,
    quality: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compress a video file by target size or quality preset.

    Args:
        input_artifact: Name of the input video artifact
        target_size_mb: Target file size in megabytes (optional)
        quality: Quality preset (high, medium, low) - used if target_size_mb not specified

    Returns:
        A dictionary with status, message, and output artifact information
    """
    plugin_name = "video-editor-tools"
    log_identifier = f"[{plugin_name}:compress_video]"
    log.info(f"{log_identifier} Compressing '{input_artifact}'")

    # Validate parameters
    if target_size_mb is None and quality is None:
        quality = "medium"  # Default

    if quality and quality not in VIDEO_QUALITY_PRESETS:
        return {
            "status": "error",
            "message": f"Invalid quality '{quality}'. Supported: {', '.join(VIDEO_QUALITY_PRESETS.keys())}"
        }

    # Validate tool context
    if not tool_context or not tool_context._invocation_context:
        return {
            "status": "error",
            "message": "ToolContext or InvocationContext is missing.",
        }

    inv_context = tool_context._invocation_context
    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        return {
            "status": "error",
            "message": "Missing required context parts for artifact operations",
        }

    temp_dir = tempfile.mkdtemp(prefix="video_compress_")
    temp_input = None
    temp_output = None

    try:
        # Load input video
        temp_input = await _load_artifact_as_temp_file(
            artifact_service, app_name, user_id, session_id,
            input_artifact, temp_dir
        )

        # Prepare output path
        input_ext = os.path.splitext(input_artifact)[1]
        temp_output = os.path.join(temp_dir, f"output{input_ext}")

        # Build compression command
        if target_size_mb:
            # Calculate target bitrate based on file size
            # First, get video duration
            probe_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                temp_input
            ]

            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            try:
                duration = float(probe_result.stdout.strip())
            except ValueError:
                duration = 60  # Default fallback

            # Calculate bitrate (in kbps)
            # target_size_mb * 8192 (convert MB to kb) / duration - audio bitrate (128k)
            target_bitrate = int((target_size_mb * 8192) / duration) - 128

            if target_bitrate < 100:
                return {
                    "status": "error",
                    "message": f"Target size {target_size_mb}MB is too small for this video duration"
                }

            cmd = [
                "ffmpeg",
                "-i", temp_input,
                "-b:v", f"{target_bitrate}k",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y",
                temp_output
            ]
            compression_method = f"target size: {target_size_mb}MB"
        else:
            # Use quality preset
            settings = VIDEO_QUALITY_PRESETS[quality]
            cmd = [
                "ffmpeg",
                "-i", temp_input,
                "-c:v", "libx264",
                "-crf", settings["crf"],
                "-preset", settings["preset"],
                "-c:a", "aac",
                "-b:a", "128k",
                "-y",
                temp_output
            ]
            compression_method = f"quality preset: {quality}"

        log.info(f"{log_identifier} Running ffmpeg compression ({compression_method})")

        # Run ffmpeg
        timeout = tool_config.get("timeout_seconds", 900) if tool_config else 900  # 15 min for compression
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} FFmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"Video compression failed: {result.stderr[:300]}"
            }

        log.info(f"{log_identifier} Compression completed successfully")

        # Read output file
        with open(temp_output, 'rb') as f:
            output_content = f.read()

        # Get original size for comparison
        original_size = os.path.getsize(temp_input)
        compressed_size = len(output_content)
        compression_ratio = (1 - compressed_size / original_size) * 100

        # Generate output filename
        timestamp = datetime.now(timezone.utc)
        input_base = os.path.splitext(input_artifact)[0]
        output_filename = f"{input_base}_compressed{input_ext}"

        # Save as artifact
        metadata_dict = {
            "description": f"Compressed video from {input_artifact}",
            "source_tool": "compress_video",
            "input_artifact": input_artifact,
            "compression_method": compression_method,
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio_percent": round(compression_ratio, 2),
            "creation_timestamp_iso": timestamp.isoformat(),
        }

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=output_content,
            mime_type=f"video/{input_ext.lstrip('.')}",
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )

        if save_result.get("status") == "error":
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        return {
            "status": "success",
            "message": f"Successfully compressed video ({compression_ratio:.1f}% reduction)",
            "output_artifact": output_filename,
            "output_version": save_result["data_version"],
            "original_size_mb": round(original_size / (1024 * 1024), 2),
            "compressed_size_mb": round(compressed_size / (1024 * 1024), 2),
            "compression_ratio_percent": round(compression_ratio, 2),
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Video compression timed out after {timeout} seconds"
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during compression: {str(e)}"
        }
    finally:
        try:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up: {e}")

# Phase 2 Tools


async def add_watermark(
    input_artifact: str,
    watermark_text: Optional[str] = None,
    watermark_image_artifact: Optional[str] = None,
    position: str = "bottom-right",
    opacity: float = 0.5,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Add a text or image watermark to a video.

    Args:
        input_artifact: Name of the input video artifact
        watermark_text: Text to use as watermark (optional)
        watermark_image_artifact: Name of watermark image artifact (optional)
        position: Watermark position (top-left, top-right, bottom-left, bottom-right, center)
        opacity: Watermark opacity (0.0 to 1.0). Default: 0.5

    Returns:
        A dictionary with status, message, and output artifact information
    """
    plugin_name = "video-editor-agent"
    log_identifier = f"[{plugin_name}:add_watermark]"
    log.info(f"{log_identifier} Adding watermark to '{input_artifact}'")

    # Validate parameters
    if not watermark_text and not watermark_image_artifact:
        return {
            "status": "error",
            "message": "Either watermark_text or watermark_image_artifact must be provided"
        }

    valid_positions = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
    if position not in valid_positions:
        return {
            "status": "error",
            "message": f"Invalid position '{position}'. Supported: {', '.join(valid_positions)}"
        }

    if not 0.0 <= opacity <= 1.0:
        return {
            "status": "error",
            "message": "Opacity must be between 0.0 and 1.0"
        }

    # Validate tool context
    if not tool_context or not tool_context._invocation_context:
        return {
            "status": "error",
            "message": "ToolContext or InvocationContext is missing.",
        }

    inv_context = tool_context._invocation_context
    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        return {
            "status": "error",
            "message": "Missing required context parts for artifact operations",
        }

    temp_dir = tempfile.mkdtemp(prefix="video_watermark_")
    temp_input = None
    temp_watermark = None
    temp_output = None

    try:
        # Load input video
        temp_input = await _load_artifact_as_temp_file(
            artifact_service, app_name, user_id, session_id,
            input_artifact, temp_dir
        )

        # Prepare output path
        input_ext = os.path.splitext(input_artifact)[1]
        temp_output = os.path.join(temp_dir, f"output{input_ext}")

        # Build filter based on watermark type
        if watermark_text:
            # Text watermark - map position to coordinates
            position_map = {
                "top-left": "x=10:y=10",
                "top-right": "x=W-tw-10:y=10",
                "bottom-left": "x=10:y=H-th-10",
                "bottom-right": "x=W-tw-10:y=H-th-10",
                "center": "x=(W-tw)/2:y=(H-th)/2"
            }

            # Create text filter with transparency
            filter_str = f"drawtext=text='{watermark_text}':{position_map[position]}:fontsize=24:fontcolor=white@{opacity}:box=1:boxcolor=black@{opacity*0.5}"

            cmd = [
                "ffmpeg",
                "-i", temp_input,
                "-vf", filter_str,
                "-codec:a", "copy",
                "-y",
                temp_output
            ]
        else:
            # Image watermark
            temp_watermark = await _load_artifact_as_temp_file(
                artifact_service, app_name, user_id, session_id,
                watermark_image_artifact, temp_dir
            )

            # Map position to overlay coordinates
            position_map = {
                "top-left": "10:10",
                "top-right": "W-w-10:10",
                "bottom-left": "10:H-h-10",
                "bottom-right": "W-w-10:H-h-10",
                "center": "(W-w)/2:(H-h)/2"
            }

            # Create overlay filter with transparency
            filter_str = f"[1]format=rgba,colorchannelmixer=aa={opacity}[wm];[0][wm]overlay={position_map[position]}"

            cmd = [
                "ffmpeg",
                "-i", temp_input,
                "-i", temp_watermark,
                "-filter_complex", filter_str,
                "-codec:a", "copy",
                "-y",
                temp_output
            ]

        log.info(f"{log_identifier} Running ffmpeg watermark")

        # Run ffmpeg
        timeout = tool_config.get("timeout_seconds", 600) if tool_config else 600
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} FFmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"Watermark addition failed: {result.stderr[:300]}"
            }

        log.info(f"{log_identifier} Watermark added successfully")

        # Read output file
        with open(temp_output, 'rb') as f:
            output_content = f.read()

        # Generate output filename
        timestamp = datetime.now(timezone.utc)
        input_base = os.path.splitext(input_artifact)[0]
        output_filename = f"{input_base}_watermarked{input_ext}"

        # Save as artifact
        watermark_type = "text" if watermark_text else "image"
        metadata_dict = {
            "description": f"Video with {watermark_type} watermark",
            "source_tool": "add_watermark",
            "input_artifact": input_artifact,
            "watermark_type": watermark_type,
            "watermark_text": watermark_text if watermark_text else None,
            "watermark_image": watermark_image_artifact if watermark_image_artifact else None,
            "position": position,
            "opacity": opacity,
            "creation_timestamp_iso": timestamp.isoformat(),
        }

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=output_content,
            mime_type=f"video/{input_ext.lstrip('.')}",
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )

        if save_result.get("status") == "error":
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        return {
            "status": "success",
            "message": f"Successfully added {watermark_type} watermark",
            "output_artifact": output_filename,
            "output_version": save_result["data_version"],
            "file_size_bytes": len(output_content),
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Watermark addition timed out after {timeout} seconds"
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during watermark addition: {str(e)}"
        }
    finally:
        try:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
            if temp_watermark and os.path.exists(temp_watermark):
                os.remove(temp_watermark)
            if temp_output and os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up: {e}")


async def resize_video(
    input_artifact: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale_preset: Optional[str] = None,
    maintain_aspect_ratio: bool = True,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Resize a video to specified dimensions or preset.

    Args:
        input_artifact: Name of the input video artifact
        width: Target width in pixels (optional if using scale_preset)
        height: Target height in pixels (optional if using scale_preset)
        scale_preset: Preset resolution (1080p, 720p, 480p, 360p) - overrides width/height
        maintain_aspect_ratio: If True, scales to fit while maintaining aspect ratio. Default: True

    Returns:
        A dictionary with status, message, and output artifact information
    """
    plugin_name = "video-editor-agent"
    log_identifier = f"[{plugin_name}:resize_video]"
    log.info(f"{log_identifier} Resizing '{input_artifact}'")

    # Scale presets
    SCALE_PRESETS = {
        "1080p": (1920, 1080),
        "720p": (1280, 720),
        "480p": (854, 480),
        "360p": (640, 360)
    }

    # Determine target dimensions
    if scale_preset:
        if scale_preset not in SCALE_PRESETS:
            return {
                "status": "error",
                "message": f"Invalid scale_preset '{scale_preset}'. Supported: {', '.join(SCALE_PRESETS.keys())}"
            }
        target_width, target_height = SCALE_PRESETS[scale_preset]
    elif width or height:
        target_width = width
        target_height = height
    else:
        return {
            "status": "error",
            "message": "Either width/height or scale_preset must be provided"
        }

    # Validate tool context
    if not tool_context or not tool_context._invocation_context:
        return {
            "status": "error",
            "message": "ToolContext or InvocationContext is missing.",
        }

    inv_context = tool_context._invocation_context
    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        return {
            "status": "error",
            "message": "Missing required context parts for artifact operations",
        }

    temp_dir = tempfile.mkdtemp(prefix="video_resize_")
    temp_input = None
    temp_output = None

    try:
        # Load input video
        temp_input = await _load_artifact_as_temp_file(
            artifact_service, app_name, user_id, session_id,
            input_artifact, temp_dir
        )

        # Prepare output path
        input_ext = os.path.splitext(input_artifact)[1]
        temp_output = os.path.join(temp_dir, f"output{input_ext}")

        # Build scale filter
        if maintain_aspect_ratio:
            if target_width and target_height:
                # Scale to fit within dimensions, maintaining aspect ratio
                scale_filter = f"scale='min({target_width},iw)':min'({target_height},ih)':force_original_aspect_ratio=decrease"
            elif target_width:
                # Scale width, auto height
                scale_filter = f"scale={target_width}:-1"
            else:
                # Scale height, auto width
                scale_filter = f"scale=-1:{target_height}"
        else:
            if not target_width or not target_height:
                return {
                    "status": "error",
                    "message": "Both width and height must be specified when maintain_aspect_ratio is False"
                }
            # Force exact dimensions
            scale_filter = f"scale={target_width}:{target_height}"

        cmd = [
            "ffmpeg",
            "-i", temp_input,
            "-vf", scale_filter,
            "-c:a", "copy",
            "-y",
            temp_output
        ]

        log.info(f"{log_identifier} Running ffmpeg resize")

        # Run ffmpeg
        timeout = tool_config.get("timeout_seconds", 600) if tool_config else 600
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} FFmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"Video resize failed: {result.stderr[:300]}"
            }

        log.info(f"{log_identifier} Resize completed successfully")

        # Read output file
        with open(temp_output, 'rb') as f:
            output_content = f.read()

        # Generate output filename
        timestamp = datetime.now(timezone.utc)
        input_base = os.path.splitext(input_artifact)[0]
        size_desc = scale_preset if scale_preset else f"{target_width}x{target_height}"
        output_filename = f"{input_base}_resized_{size_desc}{input_ext}"

        # Save as artifact
        metadata_dict = {
            "description": f"Video resized to {size_desc}",
            "source_tool": "resize_video",
            "input_artifact": input_artifact,
            "target_width": target_width,
            "target_height": target_height,
            "scale_preset": scale_preset,
            "maintain_aspect_ratio": maintain_aspect_ratio,
            "creation_timestamp_iso": timestamp.isoformat(),
        }

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=output_content,
            mime_type=f"video/{input_ext.lstrip('.')}",
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )

        if save_result.get("status") == "error":
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        return {
            "status": "success",
            "message": f"Successfully resized video to {size_desc}",
            "output_artifact": output_filename,
            "output_version": save_result["data_version"],
            "file_size_bytes": len(output_content),
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Video resize timed out after {timeout} seconds"
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during resize: {str(e)}"
        }
    finally:
        try:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up: {e}")


async def merge_videos(
    input_artifacts: str,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Merge multiple video files into a single video.

    Args:
        input_artifacts: Comma-separated list of video artifact filenames (e.g., "video1.mp4,video2.mp4,video3.mp4")

    Returns:
        A dictionary with status, message, and output artifact information
    """
    plugin_name = "video-editor-agent"
    log_identifier = f"[{plugin_name}:merge_videos]"
    log.info(f"{log_identifier} Merging videos: '{input_artifacts}'")

    # Parse input artifacts
    artifact_list = [a.strip() for a in input_artifacts.split(',')]

    if len(artifact_list) < 2:
        return {
            "status": "error",
            "message": "At least 2 video artifacts are required for merging"
        }

    # Validate tool context
    if not tool_context or not tool_context._invocation_context:
        return {
            "status": "error",
            "message": "ToolContext or InvocationContext is missing.",
        }

    inv_context = tool_context._invocation_context
    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        return {
            "status": "error",
            "message": "Missing required context parts for artifact operations",
        }

    temp_dir = tempfile.mkdtemp(prefix="video_merge_")
    temp_inputs = []
    temp_output = None
    concat_file = None

    try:
        # Load all input videos
        for idx, artifact_name in enumerate(artifact_list):
            temp_input = await _load_artifact_as_temp_file(
                artifact_service, app_name, user_id, session_id,
                artifact_name, temp_dir
            )
            # Rename to avoid conflicts
            _, ext = os.path.splitext(temp_input)
            new_path = os.path.join(temp_dir, f"input_{idx}{ext}")
            os.rename(temp_input, new_path)
            temp_inputs.append(new_path)

        # Create concat file for ffmpeg
        concat_file = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_file, 'w') as f:
            for temp_input in temp_inputs:
                # Escape single quotes in path
                escaped_path = temp_input.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        # Prepare output path
        first_ext = os.path.splitext(artifact_list[0])[1]
        temp_output = os.path.join(temp_dir, f"output{first_ext}")

        # Build ffmpeg command using concat demuxer
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",  # Copy streams without re-encoding for speed
            "-y",
            temp_output
        ]

        log.info(f"{log_identifier} Running ffmpeg merge")

        # Run ffmpeg
        timeout = tool_config.get("timeout_seconds", 900) if tool_config else 900
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} FFmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"Video merge failed: {result.stderr[:300]}"
            }

        log.info(f"{log_identifier} Merge completed successfully")

        # Read output file
        with open(temp_output, 'rb') as f:
            output_content = f.read()

        # Generate output filename
        timestamp = datetime.now(timezone.utc)
        output_filename = f"merged_video_{timestamp.strftime('%Y%m%d_%H%M%S')}{first_ext}"

        # Save as artifact
        metadata_dict = {
            "description": f"Merged video from {len(artifact_list)} sources",
            "source_tool": "merge_videos",
            "input_artifacts": artifact_list,
            "num_videos_merged": len(artifact_list),
            "creation_timestamp_iso": timestamp.isoformat(),
        }

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=output_content,
            mime_type=f"video/{first_ext.lstrip('.')}",
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )

        if save_result.get("status") == "error":
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        return {
            "status": "success",
            "message": f"Successfully merged {len(artifact_list)} videos",
            "output_artifact": output_filename,
            "output_version": save_result["data_version"],
            "file_size_bytes": len(output_content),
            "num_videos_merged": len(artifact_list),
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Video merge timed out after {timeout} seconds"
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during merge: {str(e)}"
        }
    finally:
        try:
            for temp_input in temp_inputs:
                if os.path.exists(temp_input):
                    os.remove(temp_input)
            if concat_file and os.path.exists(concat_file):
                os.remove(concat_file)
            if temp_output and os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up: {e}")


async def add_subtitles(
    input_artifact: str,
    subtitle_artifact: str,
    subtitle_style: str = "default",
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Add subtitles to a video from an SRT file.

    Args:
        input_artifact: Name of the input video artifact
        subtitle_artifact: Name of the SRT subtitle file artifact
        subtitle_style: Subtitle style preset (default, bold, large). Default: default

    Returns:
        A dictionary with status, message, and output artifact information
    """
    plugin_name = "video-editor-agent"
    log_identifier = f"[{plugin_name}:add_subtitles]"
    log.info(f"{log_identifier} Adding subtitles to '{input_artifact}'")

    # Subtitle style presets
    SUBTITLE_STYLES = {
        "default": "FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=1",
        "bold": "FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Bold=1",
        "large": "FontSize=32,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2"
    }

    if subtitle_style not in SUBTITLE_STYLES:
        return {
            "status": "error",
            "message": f"Invalid subtitle_style '{subtitle_style}'. Supported: {', '.join(SUBTITLE_STYLES.keys())}"
        }

    # Validate tool context
    if not tool_context or not tool_context._invocation_context:
        return {
            "status": "error",
            "message": "ToolContext or InvocationContext is missing.",
        }

    inv_context = tool_context._invocation_context
    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        return {
            "status": "error",
            "message": "Missing required context parts for artifact operations",
        }

    temp_dir = tempfile.mkdtemp(prefix="video_subtitles_")
    temp_input = None
    temp_subtitle = None
    temp_output = None

    try:
        # Load input video
        temp_input = await _load_artifact_as_temp_file(
            artifact_service, app_name, user_id, session_id,
            input_artifact, temp_dir
        )

        # Load subtitle file
        temp_subtitle = await _load_artifact_as_temp_file(
            artifact_service, app_name, user_id, session_id,
            subtitle_artifact, temp_dir
        )

        # Prepare output path
        input_ext = os.path.splitext(input_artifact)[1]
        temp_output = os.path.join(temp_dir, f"output{input_ext}")

        # Build subtitles filter
        # Escape the subtitle path for the filter
        escaped_subtitle = temp_subtitle.replace('\\', '\\\\').replace(':', '\\:')
        subtitle_filter = f"subtitles={escaped_subtitle}:force_style='{SUBTITLE_STYLES[subtitle_style]}'"

        cmd = [
            "ffmpeg",
            "-i", temp_input,
            "-vf", subtitle_filter,
            "-c:a", "copy",
            "-y",
            temp_output
        ]

        log.info(f"{log_identifier} Running ffmpeg subtitle addition")

        # Run ffmpeg
        timeout = tool_config.get("timeout_seconds", 600) if tool_config else 600
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} FFmpeg failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"Subtitle addition failed: {result.stderr[:300]}"
            }

        log.info(f"{log_identifier} Subtitles added successfully")

        # Read output file
        with open(temp_output, 'rb') as f:
            output_content = f.read()

        # Generate output filename
        timestamp = datetime.now(timezone.utc)
        input_base = os.path.splitext(input_artifact)[0]
        output_filename = f"{input_base}_subtitled{input_ext}"

        # Save as artifact
        metadata_dict = {
            "description": f"Video with subtitles from {subtitle_artifact}",
            "source_tool": "add_subtitles",
            "input_artifact": input_artifact,
            "subtitle_artifact": subtitle_artifact,
            "subtitle_style": subtitle_style,
            "creation_timestamp_iso": timestamp.isoformat(),
        }

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=output_content,
            mime_type=f"video/{input_ext.lstrip('.')}",
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )

        if save_result.get("status") == "error":
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        return {
            "status": "success",
            "message": "Successfully added subtitles to video",
            "output_artifact": output_filename,
            "output_version": save_result["data_version"],
            "file_size_bytes": len(output_content),
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"Subtitle addition timed out after {timeout} seconds"
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during subtitle addition: {str(e)}"
        }
    finally:
        try:
            if temp_input and os.path.exists(temp_input):
                os.remove(temp_input)
            if temp_subtitle and os.path.exists(temp_subtitle):
                os.remove(temp_subtitle)
            if temp_output and os.path.exists(temp_output):
                os.remove(temp_output)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up: {e}")
