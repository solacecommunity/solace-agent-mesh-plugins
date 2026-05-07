# SAM Graph Database Agent Plugin

## Overview

The **SAM Graph Database Agent** plugin lets Solace Agent Mesh (SAM) answer
natural-language questions against a [Neo4j](https://neo4j.com/) graph database.
The agent translates user questions into Cypher queries, executes them against
the configured database, and returns formatted results — inline for small
result sets and as artifacts (CSV / JSON / YAML) for larger ones.

It is the graph-database counterpart of the existing `sam-sql-database` plugin
and follows the same SAM v2 lifecycle / tool pattern.

## Plugin Details

- **Plugin Name**: `sam-graph-agent` (Python package: `sam_graph_database`)
- **Version**: 0.1.0
- **Author**: 
    Emil Zegers <emil.zegers@solace.com>
    Peter Kester <peter.kester@solace.com>
- **Repository**: [Solace Community Plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins)
- **Supported databases**: Neo4j (5.28+)

## Capabilities

### Natural Language → Cypher
- Translates user questions into Cypher queries using the configured LLM
- Re-tries / corrects queries when Neo4j returns an error
- Honours user-supplied query examples to bias the LLM toward known-good
  patterns

### Automatic Schema Discovery
- Calls `db.schema.visualization()` on startup; falls back to `db.labels()` /
  `db.relationshipTypes()` when the visualization procedure is unavailable
- Embeds the resulting schema (node labels, relationship types, properties)
  into the agent's system prompt so the LLM knows what it is querying
- Schema can also be overridden manually for locked-down environments

### Flexible Result Handling
- Returns small results inline in the response
- Saves all results as a SAM artifact (CSV by default; JSON or YAML on request)
- Configurable inline-size threshold; results that exceed it are truncated in
  the chat response with a pointer to the artifact

### Resource Management
- Connection pool created on agent start, closed on agent shutdown
- Configurable query timeout

## How It Works

1. **Initialization** ([`lifecycle.py`](../src/sam_graph_database/lifecycle.py)):
   on agent start, the plugin validates its config with a Pydantic model,
   opens a Neo4j driver, optionally auto-detects the schema, and builds the
   system instruction the LLM will use.
2. **Tool invocation** ([`tools.py`](../src/sam_graph_database/tools.py)): the
   LLM calls `execute_cypher_query` with a Cypher string. The tool runs the
   query, formats the result, and saves it as an artifact.
3. **Cleanup**: on shutdown, the Neo4j driver and its connections are closed.

## Prerequisites

- **Solace Agent Mesh v2** installed and configured
- **Neo4j 5.28+** reachable from the SAM host (Aura, self-hosted, Docker, …)
- **Python 3.10+** for SAM and the plugin
- **LLM credentials** already configured for SAM (the agent uses the existing
  `general_model` from `shared_config`)

## Installation

### Step 1 — Add the community plugin repository

From your SAM working directory (with the SAM virtualenv active):

```bash
sam plugin catalog
```

If you have not already added the community repo, add:

```
https://github.com/solacecommunity/solace-agent-mesh-plugins
```

### Step 2 — Install the plugin

GUI: pick **sam-graph-agent** from the catalog.

CLI:

```bash
sam plugin add graph-database --plugin sam-graph-agent
```

This wires the plugin into your SAM project and copies a default `config.yaml`
into `configs/agents/graph_database.yaml`.

### Step 3 — Configure environment variables

The default config reads its connection details from environment variables. At
minimum:

```bash
export GRAPH_DATABASE_DB_TYPE="neo4j"
export GRAPH_DATABASE_DB_HOST="bolt://localhost"   # or neo4j+s://… for Aura
export GRAPH_DATABASE_DB_PORT="7687"
export GRAPH_DATABASE_DB_USER="neo4j"
export GRAPH_DATABASE_DB_PASSWORD="your-password"
export GRAPH_DATABASE_DB_NAME="neo4j"
```

> The exact prefix (`GRAPH_DATABASE_…`) comes from the SAM-generated
> `__COMPONENT_UPPER_SNAKE_CASE_NAME__` token. If you installed the plugin
> under a different name (e.g. `sam plugin add my-knowledge-graph …`), use
> `MY_KNOWLEDGE_GRAPH_DB_*` instead.

### Step 4 — Verify the installation

Start SAM:

```bash
sam run
```

Open the SAM UI's **Agents** page; you should see the graph-database agent
listed. Ask it something like:

```
Which agents are available, and what does the graph-database agent do?
```

## Configuration Reference

The plugin's behaviour is controlled by the `agent_init_function.config` block
in the generated `config.yaml`. The full Pydantic schema lives in
[`lifecycle.py`](../src/sam_graph_database/lifecycle.py).

| Field | Required | Default | Description |
|---|---|---|---|
| `db_type` | yes | – | Must be `"neo4j"` (the only supported type today). |
| `db_host` | yes | – | Hostname or full URI (`bolt://`, `neo4j://`, `neo4j+s://`). |
| `db_port` | no | `7687` | Bolt port. Ignored if `db_host` already contains a port. |
| `db_user` | yes | – | Neo4j username. |
| `db_password` | yes | – | Neo4j password (treated as a `SecretStr`). |
| `db_name` | yes | – | Database name (`neo4j` for the default DB). |
| `query_timeout` | no | `30` | Connection / query timeout in seconds (≥ 5). |
| `database_purpose` | no | – | Free-text description of *what* the database is for. Goes into the system prompt. |
| `data_description` | no | – | Free-text description of *what data* is in the database. |
| `auto_detect_schema` | no | `true` | If false, both `database_schema_override` and `schema_summary_override` are required. |
| `database_schema_override` | conditional | – | YAML/text describing the schema in detail. Required when auto-detect is off. |
| `schema_summary_override` | conditional | – | Natural-language summary of the schema. Required when auto-detect is off. |
| `query_examples` | no | `[]` | List of `{natural_language, cypher_query}` pairs to bias the LLM. |
| `response_guidelines` | no | `""` | Guidelines appended to every tool response (e.g. data freshness disclaimers). |
| `max_inline_result_size_bytes` | no | `2048` | Inline truncation threshold; larger results are referenced via the artifact only. |

### Example: locked-down schema, no auto-detect

```yaml
agent_init_function:
  module: "sam_graph_database.lifecycle"
  name: "initialize_graph_agent"
  config:
    db_type: "neo4j"
    db_host: "neo4j+s://xxxxx.databases.neo4j.io"
    db_user: "${GRAPH_DB_USER}"
    db_password: "${GRAPH_DB_PASSWORD}"
    db_name: "neo4j"
    auto_detect_schema: false
    schema_summary_override: |
      Movie database with Person and Movie nodes. Persons act in Movies via
      ACTED_IN relationships and direct them via DIRECTED relationships.
    database_schema_override: |
      node_labels: [Person, Movie]
      relationship_types: [ACTED_IN, DIRECTED]
      node_properties:
        Person: [name, born]
        Movie:  [title, released, tagline]
      relationship_properties:
        ACTED_IN: [roles]
    query_examples:
      - natural_language: "Who directed The Matrix?"
        cypher_query: "MATCH (p:Person)-[:DIRECTED]->(m:Movie {title:'The Matrix'}) RETURN p.name"
    response_guidelines: "Always cite the movie title alongside any actor name."
```

## The `execute_cypher_query` Tool

The agent exposes a single Python tool that the LLM (or another agent) can
invoke directly:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | – | Cypher query to execute. |
| `output_filename` | `str` | auto-generated | Base filename for the artifact (extension is added automatically). |
| `result_description` | `str` | – | Human-readable description stored in the artifact's metadata. |
| `response_format` | `"yaml" \| "json" \| "csv"` | `"csv"` | Output format. |
| `inline_result` | `bool` | `true` | If true, return up to `max_inline_result_size_bytes` of the result inline. The artifact is *always* saved. |

The tool returns either:

- `status: "success_artifact_saved"` with `artifact_filename`, `artifact_version`, `row_count`, and inline `content`, or
- `status: "error"` with `error_message` and `cypher_query_attempted`.

## Usage Examples

Once the agent is running, you can talk to it in natural language through the
SAM UI or any orchestrator agent:

```
"How many Person nodes are in the database?"
```
```
"List the top 10 most-connected nodes and the types of their relationships."
```
```
"Find every Movie released after 2010 that Tom Hanks acted in,
 and save the result as a JSON artifact called tom-hanks-2010s."
```
```
"Show me the schema."
```

The LLM picks the right Cypher, calls `execute_cypher_query`, and either
returns the result inline or hands you a downloadable artifact.

## Best Practices

### Schema
- Prefer auto-detection during development; switch to `auto_detect_schema:
  false` in production for deterministic prompts and faster startup.
- Keep `database_purpose` and `data_description` short but specific — they go
  straight into the system prompt and noticeably improve query quality.

### Query Examples
- Provide 3–10 realistic `query_examples`. They are the cheapest, highest-ROI
  way to lift Cypher accuracy.
- Include the trickiest patterns (variable-length paths, aggregations,
  optional matches) — those are exactly the queries the LLM gets wrong.

### Performance
- Set `query_timeout` low enough that runaway queries don't pin the agent.
- Use `LIMIT` in your `query_examples` to teach the LLM to bound results.
- Tune `max_inline_result_size_bytes` to your UI: larger means more context in
  the chat reply, smaller means smaller LLM token bills.

### Security
- Use a Neo4j role with **read-only** privileges if the agent is exposed to
  untrusted users. The tool will happily run any Cypher the LLM emits.
- Always read `db_password` from an environment variable / secret manager,
  never inline it in `config.yaml`.
- Consider running with `auto_detect_schema: false` in production so the
  agent does not need `db.schema.*` privileges at runtime.

## Troubleshooting

**"Database handler not initialized"**
The driver failed to construct on startup. Check the SAM logs for the
underlying Neo4j error — usually wrong host, port, credentials, or a missing
`bolt://` / `neo4j+s://` scheme on `db_host`.

**`'db_user' is required for database type 'neo4j'`** (or similar)
The Pydantic config validation rejected the init config. Make sure both
`db_user` and `db_password` are set; for Aura, the user is `neo4j`.

**Schema looks empty / wrong in responses**
- The connecting role may not have `db.schema.visualization` permission. The
  service falls back to `db.labels()` / `db.relationshipTypes()`; check the
  logs for `Could not fetch schema visualization`.
- For locked-down deployments, switch to `auto_detect_schema: false` and
  provide the overrides explicitly.

**Results are always saved as artifacts even when small**
That is intentional — every result is saved so it can be referenced later. The
inline reply is a *copy*, controlled by `inline_result` and
`max_inline_result_size_bytes`.

**`Invalid response_format 'xml'`**
Only `csv`, `json`, and `yaml` are supported. Tell the LLM (via
`response_guidelines` or your prompt) which formats are acceptable.

## Development

The repository ships with a full test suite. From `sam-graph-agent/`:

```bash
hatch test                  # full matrix (Python 3.12), 50 tests
pytest tests/               # quick run with system Python; tool tests skip if
                            # google-adk / solace-agent-mesh aren't installed
```

Tests live in [`tests/`](../tests) and cover the database service, the
lifecycle init / cleanup flows, the Pydantic config model, and the
`execute_cypher_query` tool.

## Related Resources

- [Solace Agent Mesh Documentation](https://solacelabs.github.io/solace-agent-mesh/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Community Plugin Repository](https://github.com/solacecommunity/solace-agent-mesh-plugins)
