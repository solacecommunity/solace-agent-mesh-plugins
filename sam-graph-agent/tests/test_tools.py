"""Tests for sam_graph_database.tools.execute_cypher_query.

These tests run only when the external SAM and google-adk runtime dependencies
are importable; otherwise they are skipped.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("google.adk.tools")
pytest.importorskip("solace_agent_mesh.agent.utils.artifact_helpers")

from sam_graph_database.tools import execute_cypher_query  # noqa: E402


def _make_tool_context(
    db_handler=None,
    db_name="neo4j",
    response_guidelines="",
    max_inline=2048,
    artifact_service=MagicMock(),
):
    """Build a ToolContext-like MagicMock wired up as the tool expects."""
    host_component = MagicMock()
    state = {
        "db_handler": db_handler,
        "db_name": db_name,
        "db_response_guidelines": response_guidelines,
        "max_inline_result_size_bytes": max_inline,
    }
    host_component.get_agent_specific_state.side_effect = lambda key, default=None: state.get(
        key, default
    )
    host_component.get_config.side_effect = lambda key, default=None: default

    agent = MagicMock()
    agent.name = "graph-agent"
    agent.host_component = host_component

    invocation_context = MagicMock()
    invocation_context.agent = agent
    invocation_context.artifact_service = artifact_service
    invocation_context.app_name = "app"
    invocation_context.user_id = "user"

    tool_context = MagicMock()
    tool_context._invocation_context = invocation_context
    tool_context.function_call_id = "abcdef12345678"
    return tool_context, host_component


@pytest.fixture
def success_save_patch():
    with patch(
        "sam_graph_database.tools.save_artifact_with_metadata",
        new=AsyncMock(return_value={"status": "success", "data_version": 1}),
    ) as p:
        yield p


@pytest.fixture
def session_id_patch():
    with patch(
        "sam_graph_database.tools.get_original_session_id", return_value="session-1"
    ) as p:
        yield p


class TestExecuteCypherQuery:
    @pytest.mark.asyncio
    async def test_returns_error_when_tool_context_missing(self):
        result = await execute_cypher_query(query="RETURN 1", tool_context=None)
        assert result["status"] == "error"
        assert "ToolContext is missing" in result["error_message"]
        assert result["cypher_query_attempted"] == "RETURN 1"

    @pytest.mark.asyncio
    async def test_returns_error_when_host_component_missing(self):
        ctx = MagicMock()
        ctx._invocation_context.agent = MagicMock(spec=[])  # no host_component attr
        ctx._invocation_context.agent.name = "a"
        result = await execute_cypher_query(query="RETURN 1", tool_context=ctx)
        assert result["status"] == "error"
        assert "Host component not found" in result["error_message"]

    @pytest.mark.asyncio
    async def test_returns_error_when_db_handler_missing(self):
        ctx, _ = _make_tool_context(db_handler=None)
        result = await execute_cypher_query(query="RETURN 1", tool_context=ctx)
        assert result["status"] == "error"
        assert "Database handler not initialized" in result["error_message"]

    @pytest.mark.asyncio
    async def test_rejects_invalid_response_format(self):
        db_handler = MagicMock()
        ctx, _ = _make_tool_context(db_handler=db_handler)
        result = await execute_cypher_query(
            query="RETURN 1", response_format="xml", tool_context=ctx
        )
        assert result["status"] == "error"
        assert "Invalid response_format" in result["error_message"]

    @pytest.mark.asyncio
    async def test_success_csv_saves_artifact_and_returns_inline_content(
        self, success_save_patch, session_id_patch
    ):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(
            return_value=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        )
        ctx, _ = _make_tool_context(db_handler=db_handler)

        result = await execute_cypher_query(
            query="MATCH (p:Person) RETURN p.name AS name, p.age AS age",
            tool_context=ctx,
        )

        assert result["status"] == "success_artifact_saved"
        assert result["row_count"] == 2
        assert result["artifact_filename"].endswith(".csv")
        assert result["artifact_version"] == 1
        # CSV body should include header and both rows.
        assert "name,age" in result["content"]
        assert "Alice" in result["content"]
        success_save_patch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success_json_format(self, success_save_patch, session_id_patch):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(return_value=[{"n": 1}])
        ctx, _ = _make_tool_context(db_handler=db_handler)

        result = await execute_cypher_query(
            query="RETURN 1", response_format="json", tool_context=ctx
        )

        assert result["status"] == "success_artifact_saved"
        assert result["artifact_filename"].endswith(".json")
        assert '"n": 1' in result["content"]

    @pytest.mark.asyncio
    async def test_success_yaml_format(self, success_save_patch, session_id_patch):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(return_value=[{"n": 1}])
        ctx, _ = _make_tool_context(db_handler=db_handler)

        result = await execute_cypher_query(
            query="RETURN 1", response_format="yaml", tool_context=ctx
        )

        assert result["artifact_filename"].endswith(".yaml")
        assert "n: 1" in result["content"]

    @pytest.mark.asyncio
    async def test_empty_csv_result_returns_no_results_message(
        self, success_save_patch, session_id_patch
    ):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(return_value=[])
        ctx, _ = _make_tool_context(db_handler=db_handler)

        result = await execute_cypher_query(
            query="MATCH (n:DoesNotExist) RETURN n", tool_context=ctx
        )

        assert result["row_count"] == 0
        assert "No results found." in result["content"]

    @pytest.mark.asyncio
    async def test_large_result_is_truncated_inline_with_warning(
        self, success_save_patch, session_id_patch
    ):
        db_handler = MagicMock()
        # Produce a row whose CSV output comfortably exceeds the 100-byte limit.
        db_handler.execute_query = MagicMock(
            return_value=[{"value": "x" * 500}]
        )
        ctx, _ = _make_tool_context(db_handler=db_handler, max_inline=100)

        result = await execute_cypher_query(query="RETURN 1", tool_context=ctx)

        assert result["status"] == "success_artifact_saved"
        assert result["content"].endswith("...")
        assert len(result["content"]) <= 100
        assert "Warning" in result["message_to_llm"]

    @pytest.mark.asyncio
    async def test_uses_output_filename_override(
        self, success_save_patch, session_id_patch
    ):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(return_value=[{"n": 1}])
        ctx, _ = _make_tool_context(db_handler=db_handler)

        result = await execute_cypher_query(
            query="RETURN 1",
            output_filename="my_report",
            response_format="json",
            tool_context=ctx,
        )

        assert result["artifact_filename"] == "my_report.json"

    @pytest.mark.asyncio
    async def test_response_guidelines_appended_to_message(
        self, success_save_patch, session_id_patch
    ):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(return_value=[{"n": 1}])
        ctx, _ = _make_tool_context(
            db_handler=db_handler, response_guidelines="BE-TERSE"
        )

        result = await execute_cypher_query(query="RETURN 1", tool_context=ctx)

        assert "BE-TERSE" in result["message_to_llm"]

    @pytest.mark.asyncio
    async def test_query_execution_error_returned_as_error_status(
        self, success_save_patch, session_id_patch
    ):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(side_effect=RuntimeError("db exploded"))
        ctx, _ = _make_tool_context(
            db_handler=db_handler, response_guidelines="guideline"
        )

        result = await execute_cypher_query(query="BAD", tool_context=ctx)

        assert result["status"] == "error"
        assert "db exploded" in result["error_message"]
        assert "guideline" in result["error_message"]
        assert result["cypher_query_attempted"] == "BAD"
        success_save_patch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_artifact_save_failure_returned_as_error(self, session_id_patch):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(return_value=[{"n": 1}])
        ctx, _ = _make_tool_context(db_handler=db_handler)

        with patch(
            "sam_graph_database.tools.save_artifact_with_metadata",
            new=AsyncMock(
                return_value={"status": "error", "message": "disk full"}
            ),
        ):
            result = await execute_cypher_query(query="RETURN 1", tool_context=ctx)

        assert result["status"] == "error"
        assert "disk full" in result["error_message"]

    @pytest.mark.asyncio
    async def test_missing_artifact_service_returns_error(self, session_id_patch):
        db_handler = MagicMock()
        db_handler.execute_query = MagicMock(return_value=[{"n": 1}])
        ctx, _ = _make_tool_context(db_handler=db_handler, artifact_service=None)

        result = await execute_cypher_query(query="RETURN 1", tool_context=ctx)

        assert result["status"] == "error"
        assert "ArtifactService" in result["error_message"]
