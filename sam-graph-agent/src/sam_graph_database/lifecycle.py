"""
Lifecycle functions (initialization and cleanup) and Pydantic configuration model
for the Graph Database Agent Plugin.
"""

import logging
from typing import Any, Dict, List, Optional, Literal
import yaml

from datetime import datetime, timezone
from pydantic import BaseModel, Field, SecretStr, model_validator

from .services.database_service import (
    DatabaseService,
    Neo4jService,
)

log = logging.getLogger(__name__)


class GraphAgentQueryExample(BaseModel):
    natural_language: str = Field(
        description="A natural language question or statement."
    )
    cypher_query: str = Field(description="The corresponding Cypher query.")


class GraphAgentInitConfigModel(BaseModel):
    """
    Pydantic model for the configuration of the Graph Database Agent's
    initialize_graph_agent function.
    """

    db_type: Literal["neo4j"] = Field(
        description="Type of the graph database."
    )
    db_host: str = Field(
        description="Database host (required for Neo4j)."
    )
    db_port: Optional[int] = Field(
        default=7687, description="Database port (default 7687 for Neo4j bolt)."
    )
    db_user: Optional[str] = Field(
        default=None, description="Database user (required for Neo4j)."
    )
    db_password: Optional[SecretStr] = Field(
        default=None, description="Database password (required for Neo4j)."
    )
    db_name: str = Field(
        description="Database name."
    )
    query_timeout: int = Field(
        default=30, description="Query timeout in seconds.", ge=5
    )
    database_purpose: Optional[str] = Field(
        default=None,
        description="Optional: A description of the database's purpose to help the LLM.",
    )
    data_description: Optional[str] = Field(
        default=None,
        description="Optional: A detailed description of the data within the database.",
    )
    auto_detect_schema: bool = Field(
        default=True,
        description="If true, automatically detect schema. If false, overrides must be provided.",
    )
    database_schema_override: Optional[str] = Field(
        default=None,
        description="YAML/text string of the detailed database schema if auto_detect_schema is false.",
    )
    schema_summary_override: Optional[str] = Field(
        default=None,
        description="Natural language summary of the schema if auto_detect_schema is false.",
    )
    query_examples: Optional[List[GraphAgentQueryExample]] = Field(
        default=None,
        description="Optional: List of natural language to Cypher query examples.",
    )
    response_guidelines: str = Field(
        default="",
        description="Optional: Guidelines to be appended to action responses.",
    )
    max_inline_result_size_bytes: int = Field(
        default=2048,  # 2KB
        description="Maximum size (bytes) for query results to be returned inline. Larger results are saved as artifacts.",
        ge=0,
    )

    @model_validator(mode="after")
    def _validate_dependencies(self) -> "GraphAgentInitConfigModel":
        if self.db_type in ["neo4j"]:
            if self.db_user is None:
                raise ValueError(
                    "'db_user' is required for database type " + f"'{self.db_type}'"
                )
            if self.db_password is None:
                raise ValueError(
                    "'db_password' is required for database type " + f"'{self.db_type}'"
                )

        if self.auto_detect_schema is False:
            if self.database_schema_override is None:
                raise ValueError(
                    "'database_schema_override' is required when 'auto_detect_schema' is false"
                )
            if self.schema_summary_override is None:
                raise ValueError(
                    "'schema_summary_override' is required when 'auto_detect_schema' is false"
                )
        return self


def initialize_graph_agent(host_component: Any, init_config: GraphAgentInitConfigModel):
    """
    Initializes the Graph Database Agent.
    - Connects to the database.
    - Detects or loads schema information.
    - Stores necessary objects and info in host_component.agent_specific_state.
    """
    log_identifier = f"[{host_component.agent_name}:init_graph_agent]"
    log.info("%s Starting Graph Database Agent initialization...", log_identifier)

    connection_params = {
        "host": init_config.db_host,
        "port": init_config.db_port,
        "user": init_config.db_user,
        "password": (
            init_config.db_password.get_secret_value()
            if init_config.db_password
            else None
        ),
        "database": init_config.db_name,
    }

    db_service: Optional[DatabaseService] = None
    try:
        if init_config.db_type == "neo4j":
            db_service = Neo4jService(connection_params, init_config.query_timeout)
        else:
            raise ValueError(f"Unsupported database type: {init_config.db_type}")

        if not db_service or not db_service.driver:
            raise RuntimeError(
                f"Failed to initialize DatabaseService driver for type {init_config.db_type}."
            )
        log.info(
            "%s DatabaseService for type '%s' initialized successfully.",
            log_identifier,
            init_config.db_type,
        )

    except Exception as e:
        log.exception("%s Failed to initialize DatabaseService: %s", log_identifier, e)
        raise RuntimeError(f"DatabaseService initialization failed: {e}") from e

    schema_summary_for_llm: str = ""
    detailed_schema_yaml: str = ""

    try:
        if init_config.auto_detect_schema:
            log.debug("%s Auto-detecting database schema...", log_identifier)
            schema_summary_for_llm = db_service.get_schema_summary_for_llm(
                database=init_config.db_name
            )
            detailed_schema_dict = db_service.get_detailed_schema_representation(
                database=init_config.db_name
            )
            detailed_schema_yaml = yaml.dump(
                detailed_schema_dict, sort_keys=False, allow_unicode=True
            )
            log.info("%s Schema auto-detection complete.", log_identifier)
        else:
            log.debug("%s Using provided schema overrides.", log_identifier)
            if (
                not init_config.schema_summary_override
                or not init_config.database_schema_override
            ):
                raise ValueError(
                    "schema_summary_override and database_schema_override are required when auto_detect_schema is false."
                )
            schema_summary_for_llm = init_config.schema_summary_override
            detailed_schema_yaml = init_config.database_schema_override
            log.info("%s Schema overrides applied.", log_identifier)

        if not schema_summary_for_llm:
            log.warning(
                "%s Schema summary for LLM is empty. This may impact LLM performance.",
                log_identifier,
            )

    except Exception as e:
        log.exception("%s Error during schema handling: %s", log_identifier, e)
        raise RuntimeError(f"Schema handling failed: {e}") from e

    try:
        host_component.set_agent_specific_state("db_handler", db_service)
        host_component.set_agent_specific_state(
            "db_schema_summary_for_prompt", schema_summary_for_llm
        )
        host_component.set_agent_specific_state(
            "db_detailed_schema_yaml", detailed_schema_yaml
        )
        host_component.set_agent_specific_state(
            "db_query_examples", init_config.query_examples or []
        )
        host_component.set_agent_specific_state(
            "db_response_guidelines", init_config.response_guidelines or ""
        )
        host_component.set_agent_specific_state(
            "max_inline_result_size_bytes", init_config.max_inline_result_size_bytes
        )
        host_component.set_agent_specific_state("db_name", init_config.db_name)
        log.debug(
            "%s Stored database handler and schema information in agent_specific_state.",
            log_identifier,
        )
    except Exception as e:
        log.exception(
            "%s Failed to store data in agent_specific_state: %s", log_identifier, e
        )
        raise

    log.info(
        "%s Graph Database Agent initialization completed successfully.", log_identifier
    )

    try:
        db_type_for_prompt = init_config.db_type
        purpose_for_prompt = init_config.database_purpose or "Not specified."
        description_for_prompt = init_config.data_description or "Not specified."

        query_examples_list = host_component.get_agent_specific_state(
            "db_query_examples", []
        )
        formatted_query_examples = ""
        if query_examples_list:
            example_parts = []
            for ex in query_examples_list:
                nl = (
                    ex.natural_language
                    if hasattr(ex, "natural_language")
                    else ex.get("natural_language", "")
                )
                cypher = (
                    ex.cypher_query
                    if hasattr(ex, "cypher_query")
                    else ex.get("cypher_query", "")
                )
                if nl and cypher:
                    example_parts.append(f"Natural Language: {nl}\nCypher Query: {cypher}")
            if example_parts:
                formatted_query_examples = "\n\n".join(example_parts)
        current_timestamp = datetime.now(timezone.utc).isoformat()
        instruction_parts = [
            f"You are a Cypher query assistant for a {db_type_for_prompt} graph database.",
            f"The current date and time are available as: {current_timestamp}",
            "\nDATABASE CONTEXT:",
            f"Purpose: {purpose_for_prompt}",
            f"Data Description: {description_for_prompt}",
            "\nDATABASE SCHEMA:",
            detailed_schema_yaml,
            "---",
            schema_summary_for_llm,
            "---",
        ]

        if formatted_query_examples:
            instruction_parts.extend(
                [
                    "\nQUERY EXAMPLES:",
                    "---",
                    formatted_query_examples,
                    "---",
                ]
            )
        else:
            instruction_parts.append("\nQUERY EXAMPLES: Not specified.")

        instruction_parts.append(
            "\nBased on the above schema and examples, please convert user questions into Cypher queries."
        )

        final_system_instruction = "\n".join(instruction_parts)
        host_component.set_agent_system_instruction_string(final_system_instruction)
        log.debug(
            "%s System instruction string for Graph agent has been set on host_component.",
            log_identifier,
        )

    except Exception as e_instr:
        log.exception(
            "%s Failed to construct or set system instruction for Graph agent: %s",
            log_identifier,
            e_instr,
        )


def cleanup_graph_agent_resources(host_component: Any):
    """
    Cleans up resources used by the Graph Database Agent, primarily closing
    the database driver connections.
    """
    log_identifier = f"[{host_component.agent_name}:cleanup_graph_agent]"
    log.info("%s Cleaning up Graph Database Agent resources...", log_identifier)

    db_service: Optional[DatabaseService] = host_component.get_agent_specific_state(
        "db_handler"
    )

    if db_service:
        try:
            db_service.close()
            log.info("%s DatabaseService closed successfully.", log_identifier)
        except Exception as e:
            log.error(
                "%s Error closing DatabaseService: %s", log_identifier, e, exc_info=True
            )
    else:
        log.info(
            "%s No DatabaseService instance found in agent_specific_state to clean up.",
            log_identifier,
        )

    log.info("%s Graph Database Agent resource cleanup finished.", log_identifier)
