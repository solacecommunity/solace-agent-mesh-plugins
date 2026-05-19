import logging
import asyncio
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

# Available voices
AVAILABLE_VOICES = ["Carter", "Davis", "Emma", "Grace"]


async def text_to_speech(
    text: str,
    speaker_name: str = "Carter",
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Converts text to speech using VibeVoice TTS and saves the output as an MP3 artifact.

    Args:
        text: The text to convert to speech
        speaker_name: The voice to use (Carter, Davis, Emma, or Grace). Default: Carter
        tool_context: The tool context from Solace Agent Mesh
        tool_config: Additional tool configuration

    Returns:
        A dictionary with status, message, and artifact information
    """
    plugin_name = "local-tts"
    log_identifier = f"[{plugin_name}:text_to_speech]"
    log.info(f"{log_identifier} Converting text to speech with speaker: {speaker_name}")

    # Validate speaker
    if speaker_name not in AVAILABLE_VOICES:
        log.warning(f"{log_identifier} Invalid speaker '{speaker_name}', defaulting to Carter")
        speaker_name = "Carter"

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
        missing_parts = [
            part
            for part, val in [
                ("app_name", app_name),
                ("user_id", user_id),
                ("session_id", session_id),
                ("artifact_service", artifact_service),
            ]
            if not val
        ]
        log.error(f"{log_identifier} Missing required context parts: {', '.join(missing_parts)}")
        return {
            "status": "error",
            "message": f"Missing required context parts: {', '.join(missing_parts)}",
        }

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp(prefix="tts_")
    temp_text_file = None
    temp_wav_file = None
    temp_mp3_file = None

    try:
        # Write text to temporary file
        temp_text_file = os.path.join(temp_dir, "input.txt")
        with open(temp_text_file, 'w', encoding='utf-8') as f:
            f.write(text)

        log.info(f"{log_identifier} Created temporary text file: {temp_text_file}")

        # Determine paths
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        inference_script = os.path.join(plugin_dir, "realtime_model_inference_from_file.py")

        # Prepare output path
        temp_wav_file = os.path.join(temp_dir, "input_generated.wav")

        # Build command to run TTS
        # The script outputs to <output_dir>/<txt_filename>_generated.wav
        cmd = [
            "python",
            inference_script,
            "--model_path", "microsoft/VibeVoice-Realtime-0.5B",
            "--txt_path", temp_text_file,
            "--output_dir", temp_dir,
            "--speaker_name", speaker_name,
        ]

        log.info(f"{log_identifier} Running TTS command: {' '.join(cmd)}")

        # Run TTS generation
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} TTS generation failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"TTS generation failed: {result.stderr}",
            }

        log.info(f"{log_identifier} TTS generation completed successfully")

        # Check if WAV file was created
        if not os.path.exists(temp_wav_file):
            log.error(f"{log_identifier} WAV file not found at {temp_wav_file}")
            return {
                "status": "error",
                "message": "Generated WAV file not found",
            }

        # Convert WAV to MP3 using ffmpeg
        temp_mp3_file = os.path.join(temp_dir, "output.mp3")
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", temp_wav_file,
            "-codec:a", "libmp3lame",
            "-qscale:a", "2",
            "-y",  # Overwrite output file
            temp_mp3_file
        ]

        log.info(f"{log_identifier} Converting WAV to MP3")

        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            log.error(f"{log_identifier} MP3 conversion failed: {result.stderr}")
            return {
                "status": "error",
                "message": f"MP3 conversion failed: {result.stderr}",
            }

        log.info(f"{log_identifier} MP3 conversion completed successfully")

        # Read MP3 file
        with open(temp_mp3_file, 'rb') as f:
            mp3_content = f.read()

        # Generate filename
        timestamp = datetime.now(timezone.utc)
        output_filename = f"tts_{speaker_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp3"

        # Save as artifact
        metadata_dict = {
            "description": f"Text-to-speech audio generated by {plugin_name}",
            "source_tool": "text_to_speech",
            "speaker": speaker_name,
            "text_preview": text[:100] if len(text) > 100 else text,
            "creation_timestamp_iso": timestamp.isoformat(),
            "text_length": len(text),
        }

        log.info(f"{log_identifier} Saving MP3 artifact: {output_filename}")

        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=mp3_content,
            mime_type="audio/mpeg",
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

        log.info(f"{log_identifier} Artifact saved successfully: {output_filename} v{save_result['data_version']}")

        return {
            "status": "success",
            "message": f"Successfully converted text to speech with {speaker_name}'s voice",
            "output_filename": output_filename,
            "output_version": save_result["data_version"],
            "speaker": speaker_name,
            "text_length": len(text),
        }

    except subprocess.TimeoutExpired:
        log.error(f"{log_identifier} TTS generation timed out")
        return {
            "status": "error",
            "message": "TTS generation timed out",
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error during TTS generation: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during TTS generation: {str(e)}",
        }
    finally:
        # Cleanup temporary files
        try:
            if temp_text_file and os.path.exists(temp_text_file):
                os.remove(temp_text_file)
            if temp_wav_file and os.path.exists(temp_wav_file):
                os.remove(temp_wav_file)
            if temp_mp3_file and os.path.exists(temp_mp3_file):
                os.remove(temp_mp3_file)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
            log.info(f"{log_identifier} Cleaned up temporary files")
        except Exception as e:
            log.warning(f"{log_identifier} Error cleaning up temporary files: {e}")
