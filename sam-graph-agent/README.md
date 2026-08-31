# SAM Graph Database Agent

A Solace Agent Mesh plugin that provides a Graph Database agent for performing complex queries based on natural language using Neo4j.

## Description

This plugin enables natural language querying of Neo4j graph databases. The agent translates user questions into Cypher queries and returns formatted results.

## Features

- **Natural Language to Cypher**: Converts natural language questions into Cypher queries
- **Auto Schema Detection**: Automatically detects and understands the graph database schema
- **Multiple Output Formats**: Supports YAML, JSON, and CSV output formats
- **Artifact Management**: Saves large query results as artifacts
- **Configurable**: Supports custom query examples and schema overrides

## Configuration

The agent requires the following environment variables:

- `SAM_GRAPH_DATABASE_DB_TYPE`: Database type (currently supports "neo4j")
- `SAM_GRAPH_DATABASE_DB_HOST`: Neo4j database host (e.g., "bolt://localhost")
- `SAM_GRAPH_DATABASE_DB_PORT`: Neo4j database port (default: 7687)
- `SAM_GRAPH_DATABASE_DB_USER`: Neo4j username
- `SAM_GRAPH_DATABASE_DB_PASSWORD`: Neo4j password
- `SAM_GRAPH_DATABASE_DB_NAME`: Database name

## Usage

The agent provides the following tool:

### execute_cypher_query

Executes a Cypher query against the configured graph database.

**Parameters:**
- `query` (str): The Cypher query to execute
- `output_filename` (str, optional): Base name for the output artifact
- `result_description` (str, optional): Description of the query results
- `response_format` (str): Format for results - "yaml", "json", or "csv" (default: "csv")
- `inline_result` (bool): Whether to return results inline (default: True)

## Installation

```bash
pip install -e .
```

## License

Copyright (c) 2024 SolaceLabs
