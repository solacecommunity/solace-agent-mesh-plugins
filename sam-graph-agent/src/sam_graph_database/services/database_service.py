"""Service for handling graph database operations."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
import logging
import yaml
from typing import List, Dict, Any, Generator, Optional

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import Neo4jError
from neo4j.graph import Node, Relationship

log = logging.getLogger(__name__)


class DatabaseService(ABC):
    """Abstract base class for graph database services."""

    def __init__(self, connection_params: Dict[str, Any], query_timeout: int = 30):
        """Initialize the database service.

        Args:
            connection_params: Database connection parameters.
            query_timeout: Query timeout in seconds.
        """
        self.connection_params = connection_params
        self.query_timeout = query_timeout
        self.driver: Optional[Driver] = None
        try:
            self.driver = self._create_driver()
            log.info(
                "Database driver created successfully for type: %s",
                self.__class__.__name__,
            )
        except Exception as e:
            log.error("Failed to create database driver: %s", e, exc_info=True)

    @abstractmethod
    def _create_driver(self) -> Driver:
        """Create driver for database connection.

        Returns:
            Database Driver instance.
        """
        pass

    def close(self) -> None:
        """Close the driver and its connections."""
        if self.driver:
            try:
                self.driver.close()
                log.info("Database driver closed successfully.")
            except Exception as e:
                log.exception("Error closing database driver: %s", e)
        else:
            log.warning("No database driver to close.")

    @contextmanager
    def get_session(self, database: Optional[str] = None) -> Generator[Session, None, None]:
        """Get a database session.

        Args:
            database: Optional database name to use for the session.

        Yields:
            Active database session.

        Raises:
            Neo4jError: If session fails.
            RuntimeError: If the driver was not initialized.
        """
        if not self.driver:
            raise RuntimeError("Database driver is not initialized.")

        session: Optional[Session] = None
        try:
            session = self.driver.session(database=database) if database else self.driver.session()
            yield session
        except Neo4jError as e:
            log.exception("Database session error: %s", str(e))
            raise
        finally:
            if session:
                session.close()

    def execute_query(self, query: str, database: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            query: Cypher query to execute.
            database: Optional database name.

        Returns:
            List of dictionaries containing query results.

        Raises:
            Neo4jError: If query execution fails.
            RuntimeError: If the driver was not initialized.
        """
        if not self.driver:
            raise RuntimeError("Database driver is not initialized.")
        try:
            with self.get_session(database=database) as session:
                result = session.run(query)
                return result.data()
        except Neo4jError as e:
            log.exception("Query execution error: %s", str(e))
            raise

    def get_schema(self, database: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema including node labels, relationship types, and properties.

        Args:
            database: Optional database name.

        Returns:
            Dictionary containing detailed schema information.

        Raises:
            RuntimeError: If the driver was not initialized.
        """
        if not self.driver:
            raise RuntimeError("Database driver is not initialized.")

        def serialize_neo4j_schema(raw_schema):
            """Convert Neo4j objects to serializable dictionaries."""
            def convert(item):
                if isinstance(item, Node):
                    return {
                        "id": item.id,
                        "labels": list(item.labels),
                        "properties": dict(item)
                    }
                elif isinstance(item, Relationship):
                    return {
                        "id": item.id,
                        "type": item.type,
                        "start_node": item.start_node.id,
                        "end_node": item.end_node.id,
                        "properties": dict(item)
                    }
                elif isinstance(item, list):
                    return [convert(i) for i in item]
                elif isinstance(item, dict):
                    return {k: convert(v) for k, v in item.items()}
                else:
                    return item
            return convert(raw_schema)

        try:
            with self.get_session(database=database) as session:
                result = session.run("CALL db.schema.visualization()")
                schema_data = dict(result.single())
                return serialize_neo4j_schema(schema_data)
        except Exception as e:
            log.warning("Could not fetch schema visualization: %s. Falling back to basic schema detection.", e)
            return self._get_basic_schema(database)

    def _get_basic_schema(self, database: Optional[str] = None) -> Dict[str, Any]:
        """Get basic schema information when visualization is not available.

        Args:
            database: Optional database name.

        Returns:
            Dictionary containing basic schema information.
        """
        schema = {
            "node_labels": [],
            "relationship_types": [],
            "node_properties": {},
            "relationship_properties": {}
        }

        try:
            with self.get_session(database=database) as session:
                # Get node labels
                labels_result = session.run("CALL db.labels()")
                schema["node_labels"] = [record["label"] for record in labels_result]

                # Get relationship types
                rel_types_result = session.run("CALL db.relationshipTypes()")
                schema["relationship_types"] = [record["relationshipType"] for record in rel_types_result]

                # Get property keys for each node label
                for label in schema["node_labels"]:
                    props_query = f"MATCH (n:`{label}`) RETURN keys(n) AS props LIMIT 100"
                    props_result = session.run(props_query)
                    all_props = set()
                    for record in props_result:
                        all_props.update(record["props"])
                    schema["node_properties"][label] = list(all_props)

                # Get property keys for each relationship type
                for rel_type in schema["relationship_types"]:
                    props_query = f"MATCH ()-[r:`{rel_type}`]->() RETURN keys(r) AS props LIMIT 100"
                    props_result = session.run(props_query)
                    all_props = set()
                    for record in props_result:
                        all_props.update(record["props"])
                    schema["relationship_properties"][rel_type] = list(all_props)

        except Exception as e:
            log.error("Error getting basic schema: %s", e, exc_info=True)

        return schema

    def get_detailed_schema_representation(self, database: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed schema representation including all node and relationship types.

        Args:
            database: Optional database name.

        Returns:
            Dictionary containing detailed schema information.
        """
        if not self.driver:
            raise RuntimeError("Database driver is not initialized.")

        return self.get_schema(database)

    def get_schema_summary_for_llm(self, database: Optional[str] = None) -> str:
        """Gets a YAML formatted summary of the database schema for LLM prompting.

        Args:
            database: Optional database name.

        Returns:
            YAML string representation of the schema.
        """
        if not self.driver:
            raise RuntimeError("Database driver is not initialized.")

        schema_dict = self.get_detailed_schema_representation(database)

        try:
            return yaml.dump(
                schema_dict,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        except Exception as e:
            log.error("Failed to dump schema to YAML: %s", e)
            return str(schema_dict)


class Neo4jService(DatabaseService):
    """Neo4j database service implementation."""

    def _create_driver(self) -> Driver:
        """Create Neo4j database driver.

        Returns:
            Neo4j Driver instance.
        """
        host = self.connection_params.get("host")
        port = self.connection_params.get("port")
        user = self.connection_params.get("user")
        password = self.connection_params.get("password")

        # Construct Neo4j URI
        if not host:
            raise ValueError("Neo4j host is required")

        # Use bolt:// protocol by default
        if "://" not in host:
            uri = f"bolt://{host}"
            if port:
                uri += f":{port}"
        else:
            uri = host

        return GraphDatabase.driver(
            uri,
            auth=(user, password) if user and password else None,
            connection_timeout=self.query_timeout,
        )
