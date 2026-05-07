"""Tests for sam_graph_database.services.database_service."""

from unittest.mock import MagicMock, patch

import pytest
from neo4j.exceptions import Neo4jError

from sam_graph_database.services.database_service import (
    DatabaseService,
    Neo4jService,
)


@pytest.fixture
def neo4j_service(neo4j_connection_params, mock_driver):
    with patch(
        "sam_graph_database.services.database_service.GraphDatabase.driver",
        return_value=mock_driver,
    ):
        service = Neo4jService(neo4j_connection_params, query_timeout=15)
    return service


class TestNeo4jServiceDriverCreation:
    def test_creates_driver_with_bolt_uri_when_host_has_no_scheme(
        self, neo4j_connection_params, mock_driver
    ):
        with patch(
            "sam_graph_database.services.database_service.GraphDatabase.driver",
            return_value=mock_driver,
        ) as driver_factory:
            Neo4jService(neo4j_connection_params, query_timeout=15)

        driver_factory.assert_called_once()
        uri = driver_factory.call_args.args[0]
        assert uri == "bolt://localhost:7687"
        assert driver_factory.call_args.kwargs["auth"] == ("neo4j", "password")
        assert driver_factory.call_args.kwargs["connection_timeout"] == 15

    def test_preserves_existing_uri_scheme(self, mock_driver):
        params = {
            "host": "neo4j+s://example.com:7687",
            "user": "neo4j",
            "password": "pw",
        }
        with patch(
            "sam_graph_database.services.database_service.GraphDatabase.driver",
            return_value=mock_driver,
        ) as driver_factory:
            Neo4jService(params)

        assert driver_factory.call_args.args[0] == "neo4j+s://example.com:7687"

    def test_omits_auth_when_credentials_missing(self, mock_driver):
        params = {"host": "localhost", "port": 7687}
        with patch(
            "sam_graph_database.services.database_service.GraphDatabase.driver",
            return_value=mock_driver,
        ) as driver_factory:
            Neo4jService(params)

        assert driver_factory.call_args.kwargs["auth"] is None

    def test_missing_host_leaves_driver_none(self, caplog):
        # Exceptions during driver creation are caught in __init__ and logged;
        # the service is left with driver=None.
        service = Neo4jService({"user": "u", "password": "p"})
        assert service.driver is None
        assert "host is required" in caplog.text

    def test_driver_is_none_when_creation_fails(self, neo4j_connection_params, caplog):
        with patch(
            "sam_graph_database.services.database_service.GraphDatabase.driver",
            side_effect=RuntimeError("boom"),
        ):
            service = Neo4jService(neo4j_connection_params)
        assert service.driver is None


class TestSessionAndQueryExecution:
    def test_get_session_yields_and_closes_session(self, neo4j_service, mock_driver):
        session = MagicMock(name="session")
        mock_driver.session.return_value = session

        with neo4j_service.get_session() as s:
            assert s is session

        session.close.assert_called_once()
        mock_driver.session.assert_called_once_with()

    def test_get_session_passes_database_when_provided(self, neo4j_service, mock_driver):
        with neo4j_service.get_session(database="mydb"):
            pass
        mock_driver.session.assert_called_once_with(database="mydb")

    def test_get_session_raises_when_driver_not_initialized(self, neo4j_service):
        neo4j_service.driver = None
        with pytest.raises(RuntimeError, match="not initialized"):
            with neo4j_service.get_session():
                pass

    def test_execute_query_returns_result_data(self, neo4j_service, mock_driver):
        session = mock_driver.session.return_value
        run_result = MagicMock()
        run_result.data.return_value = [{"n": 1}, {"n": 2}]
        session.run.return_value = run_result

        rows = neo4j_service.execute_query("MATCH (n) RETURN n", database="mydb")

        mock_driver.session.assert_called_once_with(database="mydb")
        session.run.assert_called_once_with("MATCH (n) RETURN n")
        assert rows == [{"n": 1}, {"n": 2}]
        session.close.assert_called_once()

    def test_execute_query_raises_runtime_error_when_no_driver(self, neo4j_service):
        neo4j_service.driver = None
        with pytest.raises(RuntimeError):
            neo4j_service.execute_query("RETURN 1")

    def test_execute_query_propagates_neo4j_error(self, neo4j_service, mock_driver):
        session = mock_driver.session.return_value
        session.run.side_effect = Neo4jError("bad query")

        with pytest.raises(Neo4jError):
            neo4j_service.execute_query("BAD CYPHER")


class TestClose:
    def test_close_invokes_driver_close(self, neo4j_service, mock_driver):
        neo4j_service.close()
        mock_driver.close.assert_called_once()

    def test_close_swallows_driver_close_error(self, neo4j_service, mock_driver):
        mock_driver.close.side_effect = RuntimeError("close failed")
        # Should not raise
        neo4j_service.close()

    def test_close_with_no_driver_is_noop(self, neo4j_service):
        neo4j_service.driver = None
        neo4j_service.close()  # no exception


class TestSchemaDetection:
    def test_get_schema_falls_back_to_basic_when_visualization_unavailable(
        self, neo4j_service, mock_driver
    ):
        session = mock_driver.session.return_value
        # First call (visualization) raises; subsequent calls return schema fragments.
        labels_result = [{"label": "Person"}, {"label": "Movie"}]
        rel_types_result = [{"relationshipType": "ACTED_IN"}]
        person_props = [{"props": ["name", "age"]}]
        movie_props = [{"props": ["title"]}]
        rel_props = [{"props": ["role"]}]

        def run_side_effect(query, *args, **kwargs):
            if "db.schema.visualization" in query:
                raise RuntimeError("not available")
            if "db.labels" in query:
                return iter(labels_result)
            if "db.relationshipTypes" in query:
                return iter(rel_types_result)
            if ":`Person`" in query:
                return iter(person_props)
            if ":`Movie`" in query:
                return iter(movie_props)
            if ":`ACTED_IN`" in query:
                return iter(rel_props)
            raise AssertionError(f"unexpected query: {query}")

        session.run.side_effect = run_side_effect

        schema = neo4j_service.get_schema()

        assert schema["node_labels"] == ["Person", "Movie"]
        assert schema["relationship_types"] == ["ACTED_IN"]
        assert set(schema["node_properties"]["Person"]) == {"name", "age"}
        assert schema["node_properties"]["Movie"] == ["title"]
        assert schema["relationship_properties"]["ACTED_IN"] == ["role"]

    def test_get_schema_uses_visualization_when_available(
        self, neo4j_service, mock_driver
    ):
        session = mock_driver.session.return_value
        viz_result = MagicMock()
        viz_result.single.return_value = {"nodes": [], "relationships": []}
        session.run.return_value = viz_result

        schema = neo4j_service.get_schema(database="mydb")

        assert schema == {"nodes": [], "relationships": []}
        session.run.assert_called_once_with("CALL db.schema.visualization()")

    def test_get_schema_summary_for_llm_returns_yaml(self, neo4j_service):
        with patch.object(
            neo4j_service,
            "get_detailed_schema_representation",
            return_value={"node_labels": ["Person"]},
        ):
            yaml_str = neo4j_service.get_schema_summary_for_llm()
        assert "node_labels" in yaml_str
        assert "Person" in yaml_str

    def test_schema_methods_raise_when_driver_uninitialized(self, neo4j_service):
        neo4j_service.driver = None
        with pytest.raises(RuntimeError):
            neo4j_service.get_schema()
        with pytest.raises(RuntimeError):
            neo4j_service.get_detailed_schema_representation()
        with pytest.raises(RuntimeError):
            neo4j_service.get_schema_summary_for_llm()


class TestAbstractBase:
    def test_database_service_is_abstract(self):
        with pytest.raises(TypeError):
            DatabaseService({})  # type: ignore[abstract]
