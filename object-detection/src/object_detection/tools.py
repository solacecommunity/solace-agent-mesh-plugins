import logging
import asyncio
import inspect
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from io import BytesIO

from google.adk.tools import ToolContext
from solace_agent_mesh.agent.utils.artifact_helpers import (
    save_artifact_with_metadata,
    DEFAULT_SCHEMA_MAX_KEYS,
)
from solace_agent_mesh.agent.utils.context_helpers import get_original_session_id

from ultralytics import YOLO
from PIL import Image

log = logging.getLogger(__name__)

# COCO dataset class names (80 classes)
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book",
    "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# Module-level model cache
_yolo_model = None
_model_lock = asyncio.Lock()


async def _get_yolo_model(tool_config: Dict[str, Any]):
    """Lazy load YOLO model on first use with thread-safe caching."""
    global _yolo_model
    if _yolo_model is None:
        async with _model_lock:
            if _yolo_model is None:  # Double-check pattern
                model_name = tool_config.get("model_name", "yolo11m.pt")
                log.info(f"[ObjectDetection] Loading YOLO model: {model_name}")
                _yolo_model = await asyncio.to_thread(YOLO, model_name)
                log.info("[ObjectDetection] YOLO model loaded successfully")
    return _yolo_model


async def detect_objects_in_image(
    image_filename: str,
    objects_to_detect: list[str],
    return_bounding_boxes: bool = False,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Detects and counts specified objects in an image using YOLO model.

    The model can detect 80 object classes from the COCO dataset including:
    person, car, bicycle, dog, cat, and many more common objects.

    Args:
        image_filename: Filename with optional version (e.g., "photo.jpg" or "photo.jpg:2")
        objects_to_detect: List of COCO class names to look for
        return_bounding_boxes: If True, returns bounding boxes and confidence scores for each detection.
                              If False (default), returns only counts (backward compatible).
        tool_context: Framework context for accessing artifact service
        tool_config: Optional configuration:
            - model_name: YOLO model to use (default: "yolo11m.pt")
                         Can be a standard model (yolo11n.pt, yolo11s.pt, yolo11m.pt, etc.)
                         or a path to a custom trained model
            - confidence_threshold: Minimum confidence score (default: 0.25)

    Returns:
        Dictionary with status, message, and detections:

        When return_bounding_boxes=False (default):
            {
                "status": "success",
                "message": "Detected objects in image successfully",
                "image_filename": "photo.jpg",
                "image_version": 1,
                "detections": {"person": 3, "car": 2}
            }

        When return_bounding_boxes=True:
            {
                "status": "success",
                "message": "Detected objects in image successfully",
                "image_filename": "photo.jpg",
                "image_version": 1,
                "detections": {
                    "person": [
                        {
                            "bbox": {"x1": 100.5, "y1": 50.2, "x2": 300.8, "y2": 400.1},
                            "confidence": 0.92
                        },
                        ...
                    ],
                    "car": [...]
                },
                "total_count": {"person": 3, "car": 2}
            }
    """
    log_identifier = f"[ObjectDetection:detect_objects_in_image:{image_filename}]"

    if not tool_context:
        log.error(f"{log_identifier} ToolContext is missing.")
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
            raise ValueError(
                f"Missing required context parts: {', '.join(missing_parts)}"
            )

        log.info(f"{log_identifier} Processing request for session {session_id}.")

        # Get tool configuration
        current_tool_config = tool_config if tool_config is not None else {}
        confidence_threshold = current_tool_config.get("confidence_threshold", 0.25)

        # Validate objects_to_detect
        normalized_objects = [obj.lower() for obj in objects_to_detect]
        invalid_objects = [obj for obj in normalized_objects if obj not in COCO_CLASSES]

        if invalid_objects:
            raise ValueError(
                f"Invalid COCO class names: {invalid_objects}. "
                f"Valid classes are: {', '.join(COCO_CLASSES)}"
            )

        log.debug(f"{log_identifier} Looking for objects: {normalized_objects}")

        # Parse image filename and version
        parts = image_filename.rsplit(":", 1)
        filename_base_for_load = parts[0]
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
                    filename=filename_base_for_load,
                )
            else:
                versions = await asyncio.to_thread(
                    list_versions_method,
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id,
                    filename=filename_base_for_load,
                )
            if not versions:
                raise FileNotFoundError(
                    f"Image artifact '{filename_base_for_load}' not found."
                )
            version_to_load = max(versions)
            log.debug(
                f"{log_identifier} Using latest version for input: {version_to_load}"
            )

        # Load image artifact
        load_artifact_method = getattr(artifact_service, "load_artifact")
        if inspect.iscoroutinefunction(load_artifact_method):
            image_artifact_part = await load_artifact_method(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename_base_for_load,
                version=version_to_load,
            )
        else:
            image_artifact_part = await asyncio.to_thread(
                load_artifact_method,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename_base_for_load,
                version=version_to_load,
            )

        if not image_artifact_part or not image_artifact_part.inline_data:
            raise FileNotFoundError(
                f"Content for image artifact '{filename_base_for_load}' v{version_to_load} not found."
            )

        image_bytes = image_artifact_part.inline_data.data
        log.debug(f"{log_identifier} Loaded image artifact: {len(image_bytes)} bytes")

        # Convert to PIL Image
        pil_image = Image.open(BytesIO(image_bytes))
        log.debug(
            f"{log_identifier} Converted to PIL Image: {pil_image.size}, mode: {pil_image.mode}"
        )

        # Load YOLO model
        model = await _get_yolo_model(current_tool_config)

        # Run inference
        log.info(f"{log_identifier} Running YOLO inference...")
        results = await asyncio.to_thread(
            model.predict,
            pil_image,
            conf=confidence_threshold,
            verbose=False
        )

        # Parse results and count/extract detections
        if return_bounding_boxes:
            # Initialize detections as lists for bounding box data
            detections = {obj: [] for obj in normalized_objects}
        else:
            # Initialize detections as counts (backward compatible)
            detections = {obj: 0 for obj in normalized_objects}

        if results and len(results) > 0:
            result = results[0]  # First (and only) image result

            if result.boxes is not None and len(result.boxes) > 0:
                # Get class indices
                class_indices = result.boxes.cls.cpu().numpy()

                if return_bounding_boxes:
                    # Extract bounding boxes and confidence scores
                    boxes_xyxy = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()

                    for idx, class_idx in enumerate(class_indices):
                        class_name = model.names[int(class_idx)]
                        class_name_lower = class_name.lower()

                        # Add detection with bbox and confidence if requested
                        if class_name_lower in normalized_objects:
                            bbox = boxes_xyxy[idx]
                            detections[class_name_lower].append({
                                "bbox": {
                                    "x1": float(bbox[0]),
                                    "y1": float(bbox[1]),
                                    "x2": float(bbox[2]),
                                    "y2": float(bbox[3])
                                },
                                "confidence": float(confidences[idx])
                            })
                else:
                    # Just count detections (original behavior)
                    for class_idx in class_indices:
                        class_name = model.names[int(class_idx)]
                        class_name_lower = class_name.lower()

                        # Count if it's one of the requested objects
                        if class_name_lower in normalized_objects:
                            detections[class_name_lower] += 1

                log.debug(f"{log_identifier} Raw detections: {detections}")

        # Calculate total count
        if return_bounding_boxes:
            total_count = sum(len(dets) for dets in detections.values())
            count_summary = {obj: len(dets) for obj, dets in detections.items()}
        else:
            total_count = sum(detections.values())

        log.info(
            f"{log_identifier} Detection completed. Found: {total_count} objects"
        )

        # Build return dictionary
        result_dict = {
            "status": "success",
            "message": "Detected objects in image successfully",
            "image_filename": filename_base_for_load,
            "image_version": version_to_load,
            "detections": detections,
        }

        # Add total_count summary when returning bounding boxes
        if return_bounding_boxes:
            result_dict["total_count"] = count_summary

        return result_dict

    except FileNotFoundError as e:
        log.warning(f"{log_identifier} File not found error: {e}")
        return {"status": "error", "message": str(e)}
    except ValueError as ve:
        log.error(f"{log_identifier} Value error: {ve}")
        return {"status": "error", "message": str(ve)}
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error in detect_objects_in_image: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}


async def example_text_processor_tool(
    text_input: str,
    uppercase: bool = False,  # Example of a boolean parameter
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    An example tool that processes input text, optionally converts it to uppercase,
    and adds a prefix from tool_config.
    """
    plugin_name = "object detection"
    log_identifier = f"[{plugin_name}:example_text_processor_tool]"
    log.info(f"{log_identifier} Received text: '{text_input}', uppercase: {uppercase}")

    current_tool_config = tool_config if tool_config is not None else {}
    prefix = current_tool_config.get("prefix", "Processed: ")

    processed_text = text_input
    if uppercase:
        processed_text = processed_text.upper()

    final_text = f"{prefix}{processed_text}"

    log.info(f"{log_identifier} Processed text: '{final_text}'")
    return {
        "status": "success",
        "message": "Text processed successfully by example_text_processor_tool.",
        "original_input": text_input,
        "processed_text": final_text,
        "was_uppercased": uppercase,
    }


async def example_text_file_creator_tool(
    filename: str,
    content: str,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    An example tool that creates a text file and saves it as an artifact
    using the Solace Agent Mesh artifact service.
    """
    plugin_name = "object detection"
    log_identifier = f"[{plugin_name}:example_text_file_creator_tool]"
    log.info(
        f"{log_identifier} Received request to create file: '{filename}' with content starting: '{content[:50]}...'"
    )

    if not tool_context or not tool_context._invocation_context:
        log.error(
            f"{log_identifier} ToolContext or InvocationContext is missing. Cannot save artifact."
        )
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
        log.error(
            f"{log_identifier} Missing required context parts for artifact saving: {', '.join(missing_parts)}"
        )
        return {
            "status": "error",
            "message": f"Missing required context parts for artifact saving: {', '.join(missing_parts)}",
        }

    output_filename = filename
    if not output_filename.lower().endswith(".txt"):
        output_filename += ".txt"

    content_bytes = content.encode("utf-8")
    mime_type = "text/plain"
    timestamp = datetime.now(timezone.utc)

    metadata_dict = {
        "description": f"Text file created by {plugin_name}'s example_text_file_creator_tool.",
        "source_tool": "example_text_file_creator_tool",
        "original_requested_filename": filename,
        "creation_timestamp_iso": timestamp.isoformat(),
        "content_character_count": len(content),
    }

    log.info(
        f"{log_identifier} Attempting to save artifact '{output_filename}' via artifact_service."
    )
    try:
        save_result = await save_artifact_with_metadata(
            artifact_service=artifact_service,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=output_filename,
            content_bytes=content_bytes,
            mime_type=mime_type,
            metadata_dict=metadata_dict,
            timestamp=timestamp,
            schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
            tool_context=tool_context,
        )
        if save_result.get("status") == "error":
            log.error(
                f"{log_identifier} Failed to save artifact: {save_result.get('message')}"
            )
            return {
                "status": "error",
                "message": f"Failed to save artifact: {save_result.get('message')}",
            }

        log.info(
            f"{log_identifier} Artifact '{output_filename}' v{save_result['data_version']} saved successfully."
        )
        return {
            "status": "success",
            "message": f"File '{output_filename}' created and saved as artifact v{save_result['data_version']}.",
            "output_filename": output_filename,
            "output_version": save_result["data_version"],
        }
    except Exception as e:
        log.exception(f"{log_identifier} Unexpected error during artifact saving: {e}")
        return {
            "status": "error",
            "message": f"An unexpected error occurred during artifact saving: {e}",
        }


# Example of how these might be tested or run if this file was executed directly.
# This assumes the script is run in an environment where solace_agent_mesh is importable,
# or the imports at the top will fail.
if __name__ == "__main__":

    async def run_tests():
        print("--- Testing example_text_processor_tool ---")
        # For standalone testing, ToolContext might be minimal or None if ADK is not fully available.
        # The tool should handle tool_context=None gracefully if it's designed to be testable standalone.

        # A more complete mock for standalone testing if needed:
        class MockArtifactService:
            async def save_artifact(
                self, **kwargs
            ):  # Match expected signature elements
                log.info(
                    f"MockArtifactService.save_artifact called with filename: {kwargs.get('filename')}"
                )
                return {
                    "uri": f"mock://{kwargs.get('filename')}",
                    "version": 1,
                }  # Simulate ADK response

            async def save_artifact_metadata(self, **kwargs):
                log.info(
                    f"MockArtifactService.save_artifact_metadata called for: {kwargs.get('filename')}"
                )
                return {
                    "uri": f"mock://{kwargs.get('filename')}.metadata",
                    "version": 1,
                }

        class MockInvocationContext:
            def __init__(self):
                self.app_name = "test_app"
                self.user_id = "test_user"
                self.session_id = "test_session_123"
                self.artifact_service = MockArtifactService()
                # Add other attributes if your tool or helpers expect them

        class MockToolContext:
            def __init__(self):
                self._invocation_context = MockInvocationContext()

        mock_context = MockToolContext()

        text_result1 = await example_text_processor_tool(
            "hello world",
            uppercase=True,
            tool_context=mock_context,
            tool_config={"prefix": "TestPrefix: "},
        )
        print(f"Text tool result 1: {text_result1}")

        text_result2 = await example_text_processor_tool(
            "another test", tool_context=mock_context
        )
        print(f"Text tool result 2: {text_result2}")

        print("\n--- Testing example_text_file_creator_tool ---")
        file_result = await example_text_file_creator_tool(
            "my_example_file.txt",
            "This is the content of the example file created by the plugin template.",
            tool_context=mock_context,  # Using the mock context with a mock artifact service
        )
        print(f"File tool result: {file_result}")

    asyncio.run(run_tests())
