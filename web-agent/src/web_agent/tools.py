import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Literal

from google.adk.tools import ToolContext
from solace_agent_mesh.agent.utils.artifact_helpers import (
    save_artifact_with_metadata,
    DEFAULT_SCHEMA_MAX_KEYS,
)
from solace_agent_mesh.agent.utils.context_helpers import get_original_session_id

from ddgs import DDGS

logger = logging.getLogger(__name__)


async def web_search(
    query: str,
    search_type: Literal["text", "images", "videos", "news"] = "text",
    max_results: int = 10,
    save_as_artifact: bool = True,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo search engine.

    Supports multiple search types: text (web pages), images, videos, and news.
    Results can be returned as structured data and optionally saved as artifacts.

    Args:
        query: Search query string
        search_type: Type of search - "text", "images", "videos", or "news" (default: "text")
        max_results: Maximum number of results to return (default: 10)
        save_as_artifact: Whether to save results as a JSON artifact (default: True)
        tool_context: Framework context for accessing artifact service
        tool_config: Optional configuration

    Returns:
        Dictionary with status, message, results, and optionally artifact information
    """
    log_identifier = f"[WebSearch:web_search:{search_type}:{query[:50]}]"
    logger.info(f"{log_identifier} Searching with max_results={max_results}")

    try:
        # Perform search using ddgs library
        logger.debug(f"{log_identifier} Initiating DuckDuckGo search")

        # Run search in thread pool since ddgs is synchronous
        results = await asyncio.to_thread(_perform_search, query, search_type, max_results)

        if not results:
            logger.warning(f"{log_identifier} No results found")
            return {
                "status": "success",
                "message": f"No results found for query: {query}",
                "results": [],
                "result_count": 0,
            }

        logger.info(f"{log_identifier} Found {len(results)} results")

        # Prepare response
        response = {
            "status": "success",
            "message": f"Found {len(results)} {search_type} results",
            "search_type": search_type,
            "query": query,
            "results": results,
            "result_count": len(results),
        }

        # Save as artifact if requested and tool_context is available
        if save_as_artifact and tool_context:
            try:
                artifact_result = await _save_search_results_artifact(
                    query=query,
                    search_type=search_type,
                    results=results,
                    tool_context=tool_context,
                    log_identifier=log_identifier,
                )
                response["artifact_filename"] = artifact_result["filename"]
                response["artifact_version"] = artifact_result["version"]
                logger.info(f"{log_identifier} Saved results as artifact: {artifact_result['filename']}")
            except Exception as e:
                logger.warning(f"{log_identifier} Failed to save artifact: {e}")
                response["artifact_error"] = str(e)

        return response

    except Exception as e:
        logger.exception(f"{log_identifier} Unexpected error during search: {e}")
        return {
            "status": "error",
            "message": f"Search failed: {e}",
            "search_type": search_type,
            "query": query,
        }


def _perform_search(
    query: str,
    search_type: str,
    max_results: int
) -> List[Dict[str, Any]]:
    """
    Perform the actual search using ddgs library (synchronous).

    Args:
        query: Search query
        search_type: Type of search (text, images, videos, news)
        max_results: Maximum number of results

    Returns:
        List of search results
    """
    ddgs = DDGS()
    results = []

    try:
        if search_type == "text":
            # Web search
            search_results = ddgs.text(query, max_results=max_results)
            for item in search_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                })

        elif search_type == "images":
            # Image search
            search_results = ddgs.images(query, max_results=max_results)
            for item in search_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "image_url": item.get("image", ""),
                    "thumbnail": item.get("thumbnail", ""),
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "source": item.get("source", ""),
                })

        elif search_type == "videos":
            # Video search
            search_results = ddgs.videos(query, max_results=max_results)
            for item in search_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("content", ""),
                    "description": item.get("description", ""),
                    "duration": item.get("duration", ""),
                    "publisher": item.get("publisher", ""),
                    "published": item.get("published", ""),
                    "thumbnail": item.get("images", {}).get("large", ""),
                })

        elif search_type == "news":
            # News search
            search_results = ddgs.news(query, max_results=max_results)
            for item in search_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("body", ""),
                    "date": item.get("date", ""),
                    "source": item.get("source", ""),
                })
        else:
            raise ValueError(f"Unsupported search type: {search_type}")

    except Exception as e:
        logger.error(f"Error performing {search_type} search: {e}")
        raise

    return results


async def _save_search_results_artifact(
    query: str,
    search_type: str,
    results: List[Dict[str, Any]],
    tool_context: ToolContext,
    log_identifier: str,
) -> Dict[str, Any]:
    """
    Save search results as a JSON artifact.

    Args:
        query: Search query
        search_type: Type of search
        results: Search results
        tool_context: Framework context
        log_identifier: Log identifier string

    Returns:
        Dictionary with filename and version
    """
    inv_context = tool_context._invocation_context
    if not inv_context:
        raise ValueError("InvocationContext is not available.")

    app_name = getattr(inv_context, "app_name", None)
    user_id = getattr(inv_context, "user_id", None)
    session_id = get_original_session_id(inv_context)
    artifact_service = getattr(inv_context, "artifact_service", None)

    if not all([app_name, user_id, session_id, artifact_service]):
        raise ValueError("Missing required context parts for artifact saving")

    # Create filename based on query and search type
    safe_query = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in query)
    safe_query = safe_query.replace(' ', '_')[:50]  # Limit length
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"search_{search_type}_{safe_query}_{timestamp_str}.json"

    # Create JSON content
    content_data = {
        "query": query,
        "search_type": search_type,
        "result_count": len(results),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    content_bytes = json.dumps(content_data, indent=2, ensure_ascii=False).encode("utf-8")

    # Prepare metadata
    timestamp = datetime.now(timezone.utc)
    metadata_dict = {
        "description": f"DuckDuckGo {search_type} search results for: {query}",
        "source_tool": "web_search",
        "query": query,
        "search_type": search_type,
        "result_count": len(results),
        "creation_timestamp_iso": timestamp.isoformat(),
    }

    # Save artifact
    save_result = await save_artifact_with_metadata(
        artifact_service=artifact_service,
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename=filename,
        content_bytes=content_bytes,
        mime_type="application/json",
        metadata_dict=metadata_dict,
        timestamp=timestamp,
        schema_max_keys=DEFAULT_SCHEMA_MAX_KEYS,
        tool_context=tool_context,
    )

    if save_result.get("status") == "error":
        raise Exception(f"Failed to save artifact: {save_result.get('message')}")

    return {
        "filename": filename,
        "version": save_result["data_version"],
    }
