"""Tests for sam_graph_database.lifecycle."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr, ValidationError

from sam_graph_database.lifecycle import (
    GraphAgentInitConfigModel,
    GraphAgentQueryExample,
    cleanup_graph_agent_resources,
    initialize_graph_agent,
)


def _minimal_config_kwargs(**overrides):
    base = {
        "db_type": "neo4j",
        "db_host": "localhost",
        "db_port": 7687,
        "db_user": "neo4j",
        "db_password": SecretStr("password"),
        "db_name": "neo4j",
    }
    base.update(overrides)
    return base


class TestGraphAgentInitConfigModel:
    def test_valid_config(self):
        cfg = GraphAgentInitConfigModel(**_minimal_config_kwargs())
        assert cfg.db_type == "neo4j"
        assert cfg.auto_detect_schema is True
        assert cfg.query_timeout == 30
        assert cfg.max_inline_result_size_bytes == 2048

    def test_neo4j_requires_user(self):
        with pytest.raises(ValidationError, match="db_user"):
            GraphAgentInitConfigModel(**_minimal_config_kwargs(db_user=None))

    def test_neo4j_requires_password(self):
        with pytest.raises(ValidationError, match="db_password"):
            GraphAgentInitConfigModel(**_minimal_config_kwargs(db_password=None))

    def test_rejects_unsupported_db_type(self):
        with pytest.raises(ValidationError):
            GraphAgentInitConfigModel(**_minimal_config_kwargs(db_type="postgres"))

    def test_query_timeout_minimum(self):
        with pytest.raises(ValidationError):
            GraphAgentInitConfigModel(**_minimal_config_kwargs(query_timeout=1))

    def test_schema_overrides_required_when_auto_detect_disabled(self):
        with pytest.raises(ValidationError, match="database_schema_override"):
            GraphAgentInitConfigModel(
                **_minimal_config_kwargs(auto_detect_schema=False)
            )

    def test_schema_overrides_accepted_when_auto_detect_disabled(self):
        cfg = GraphAgentInitConfigModel(
            **_minimal_config_kwargs(
                auto_detect_schema=False,
                database_schema_override="nodes: []",
                schema_summary_override="summary",
            )
        )
        assert cfg.auto_detect_schema is False
        assert cfg.schema_summary_override == "summary"

    def test_query_examples_accepts_list_of_models(self):
        cfg = GraphAgentInitConfigModel(
            **_minimal_config_kwargs(
                query_examples=[
                    {"natural_language": "all people", "cypher_query": "MATCH (p:Person) RETURN p"},
                ]
            )
        )
        assert len(cfg.query_examples) == 1
        assert isinstance(cfg.query_examples[0], GraphAgentQueryExample)
        assert cfg.query_examples[0].cypher_query.startswith("MATCH")

    def test_negative_max_inline_size_rejected(self):
        with pytest.raises(ValidationError):
            GraphAgentInitConfigModel(
                **_minimal_config_kwargs(max_inline_result_size_bytes=-1)
            )


@pytest.fixture
def host_component():
    hc = MagicMock()
    hc.agent_name = "test-graph-agent"
    state = {}

    def _set(key, value):
        state[key] = value

    def _get(key, default=None):
        return state.get(key, default)

    hc.set_agent_specific_state.side_effect = _set
    hc.get_agent_specific_state.side_effect = _get
    hc._state = state
    return hc


class TestInitializeGraphAgent:
    def test_initializes_service_and_stores_state_with_auto_schema(
        self, host_component
    ):
        cfg = GraphAgentInitConfigModel(
            **_minimal_config_kwargs(
                database_purpose="Knowledge graph",
                data_description="People and movies",
                query_examples=[
                    {"natural_language": "actors in X", "cypher_query": "MATCH..."},
                ],
                response_guidelines="Keep it short.",
            )
        )
        db_service = MagicMock(name="Neo4jService")
        db_service.driver = MagicMock()
        db_service.get_schema_summary_for_llm.return_value = "schema-summary"
        db_service.get_detailed_schema_representation.return_value = {"node_labels": ["Person"]}

        with patch(
            "sam_graph_database.lifecycle.Neo4jService", return_value=db_service
        ) as neo4j_cls:
            initialize_graph_agent(host_component, cfg)

        neo4j_cls.assert_called_once()
        params, timeout = neo4j_cls.call_args.args
        assert params == {
            "host": "localhost",
            "port": 7687,
            "user": "neo4j",
            "password": "password",
            "database": "neo4j",
        }
        assert timeout == 30

        state = host_component._state
        assert state["db_handler"] is db_service
        assert state["db_schema_summary_for_prompt"] == "schema-summary"
        assert "node_labels" in state["db_detailed_schema_yaml"]
        assert state["db_response_guidelines"] == "Keep it short."
        assert state["db_name"] == "neo4j"
        assert state["max_inline_result_size_bytes"] == 2048

        host_component.set_agent_system_instruction_string.assert_called_once()
        instruction = host_component.set_agent_system_instruction_string.call_args.args[0]
        assert "Cypher query assistant" in instruction
        assert "Knowledge graph" in instruction
        assert "People and movies" in instruction
        assert "QUERY EXAMPLES:" in instruction
        assert "MATCH..." in instruction

    def test_uses_schema_overrides_when_auto_detect_disabled(self, host_component):
        cfg = GraphAgentInitConfigModel(
            **_minimal_config_kwargs(
                auto_detect_schema=False,
                database_schema_override="override-yaml",
                schema_summary_override="override-summary",
            )
        )
        db_service = MagicMock()
        db_service.driver = MagicMock()

        with patch(
            "sam_graph_database.lifecycle.Neo4jService", return_value=db_service
        ):
            initialize_graph_agent(host_component, cfg)

        db_service.get_schema_summary_for_llm.assert_not_called()
        db_service.get_detailed_schema_representation.assert_not_called()
        assert host_component._state["db_schema_summary_for_prompt"] == "override-summary"
        assert host_component._state["db_detailed_schema_yaml"] == "override-yaml"

    def test_instruction_says_not_specified_when_no_examples(self, host_component):
        cfg = GraphAgentInitConfigModel(**_minimal_config_kwargs())
        db_service = MagicMock()
        db_service.driver = MagicMock()
        db_service.get_schema_summary_for_llm.return_value = "summary"
        db_service.get_detailed_schema_representation.return_value = {}

        with patch(
            "sam_graph_database.lifecycle.Neo4jService", return_value=db_service
        ):
            initialize_graph_agent(host_component, cfg)

        instruction = host_component.set_agent_system_instruction_string.call_args.args[0]
        assert "QUERY EXAMPLES: Not specified." in instruction

    def test_raises_when_driver_not_created(self, host_component):
        cfg = GraphAgentInitConfigModel(**_minimal_config_kwargs())
        broken_service = MagicMock()
        broken_service.driver = None

        with patch(
            "sam_graph_database.lifecycle.Neo4jService", return_value=broken_service
        ):
            with pytest.raises(RuntimeError, match="DatabaseService initialization failed"):
                initialize_graph_agent(host_component, cfg)

    def test_raises_when_service_constructor_fails(self, host_component):
        cfg = GraphAgentInitConfigModel(**_minimal_config_kwargs())

        with patch(
            "sam_graph_database.lifecycle.Neo4jService",
            side_effect=RuntimeError("connect failed"),
        ):
            with pytest.raises(RuntimeError, match="DatabaseService initialization failed"):
                initialize_graph_agent(host_component, cfg)


class TestCleanup:
    def test_closes_db_service_when_present(self, host_component):
        db_service = MagicMock()
        host_component._state["db_handler"] = db_service

        cleanup_graph_agent_resources(host_component)

        db_service.close.assert_called_once()

    def test_is_noop_when_no_handler(self, host_component):
        # Should not raise when there is nothing to clean up.
        cleanup_graph_agent_resources(host_component)

    def test_swallows_close_errors(self, host_component):
        db_service = MagicMock()
        db_service.close.side_effect = RuntimeError("boom")
        host_component._state["db_handler"] = db_service

        # Should not raise
        cleanup_graph_agent_resources(host_component)
        db_service.close.assert_called_once()
