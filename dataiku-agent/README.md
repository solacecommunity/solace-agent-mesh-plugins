# Dataiku Agent SAM Plugin

A Solace Agent Mesh (SAM) plugin that enables seamless invocation of Dataiku AI agents through the SAM ecosystem.

[Dataiku Documentation](https://doc.dataiku.com/)

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) and is not officially supported by Solace. For community support, please open an issue in this repository. 
⭐️ Please leave a star on the [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) repo while you are there. 

---

## Overview

The Dataiku Agent plugin acts as a bridge between Solace Agent Mesh and Dataiku's AI agents, enabling SAM agents to delegate specialized tasks to Dataiku agents via the Dataiku Python API. This integration allows you to leverage Dataiku's powerful AI capabilities within your SAM multi-agent workflows.

This plugin provides a configuration-first approach with YAML-based agent definitions and Python tools that handle the communication with Dataiku's API. It supports both streaming and non-streaming responses, and can extract sources and artifacts returned by Dataiku agents.

Use cases include:
- Delegating data analysis tasks to Dataiku agents
- Leveraging Dataiku's specialized AI models within SAM workflows
- Creating hybrid agent systems that combine SAM's orchestration with Dataiku's AI capabilities
- Building complex multi-agent systems that span both platforms

## Features

This agent provides the following capabilities:

- **Invoke Dataiku Agents**: Send messages to Dataiku AI agents and receive responses with full support for sources and artifacts
- **Agent Discovery**: List all available Dataiku agents in your project to discover what capabilities are available
- **Agent Metadata**: Retrieve detailed information about specific agents including their configuration and capabilities
- **Streaming Support**: Handle both streaming and non-streaming responses from Dataiku agents
- **Error Handling**: Comprehensive error handling with clear messages for authentication, connection, and agent-related issues
- **A2A Protocol**: Full support for Agent-to-Agent communication within the SAM ecosystem

## Configuration

The plugin requires the following environment variables to be set:

- `DATAIKU_INSTANCE_URL`: Your Dataiku DSS instance URL (e.g., `https://your-instance.dataiku.com`)
- `DATAIKU_API_KEY`: API key for authentication with your Dataiku instance
- `DATAIKU_DEFAULT_PROJECT`: (Optional) Default project key to use when not specified in tool calls

### Obtaining Dataiku Credentials

1. **Instance URL**: This is the URL of your Dataiku DSS instance
2. **API Key**: Generate an API key in Dataiku:
   - Go to your Dataiku instance
   - Navigate to your user profile settings
   - Create a new API key with appropriate permissions
   - Copy the key and set it as the `DATAIKU_API_KEY` environment variable

3. **Project Key**: Find your project key in Dataiku:
   - Open your project in Dataiku
   - The project key is visible in the project settings or URL

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin dataiku-agent`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=dataiku-agent
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add [component-name] --plugin dataiku-agent`
4. Configure required environment variables (see Configuration section above)

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts.

### Example Prompts

- *"List all available Dataiku agents in my project"*
- *"Invoke the data analysis agent with the message: Analyze the sales trends for Q4"*
- *"Get information about the agent with ID agent:abc123xyz"*
- *"Use the Dataiku forecasting agent to predict next month's revenue"*
- *"What agents are available in the MARKETING project?"*

### Tools Available

The agent includes the following tools:

- **`invoke_dataiku_agent`**: Invoke a Dataiku AI agent with a message and receive the response, including any sources or artifacts
  - Parameters:
    - `agent_id` (required): The Dataiku agent ID (format: `agent:xxxxxxxx`)
    - `message` (required): The message to send to the agent
    - `project_key` (optional): Project key (uses default if not provided)
    - `stream` (optional): Whether to use streaming responses (default: false)

- **`list_dataiku_agents`**: List all available Dataiku agents in the project
  - Parameters:
    - `project_key` (optional): Project key (uses default if not provided)

- **`get_agent_info`**: Get detailed information about a specific Dataiku agent
  - Parameters:
    - `agent_id` (required): The Dataiku agent ID (format: `agent:xxxxxxxx`)
    - `project_key` (optional): Project key (uses default if not provided)

### Response Structure

When invoking a Dataiku agent, the response includes:

```json
{
  "success": true,
  "text": "Agent response text",
  "sources": [
    {
      "title": "Source document title",
      "url": "Source URL",
      "content": "Relevant content excerpt"
    }
  ],
  "artifacts": [
    {
      "type": "artifact type",
      "data": "artifact data"
    }
  ],
  "error": null,
  "metadata": {
    "agent_id": "agent:xxxxxxxx",
    "project_key": "PROJECT_KEY",
    "timestamp": "2024-01-01T12:00:00Z",
    "streaming": false
  }
}
```

## External Services

This plugin utilizes the following external service(s):

- **[Dataiku DSS](https://www.dataiku.com/)**: Data Science Studio platform that provides AI agents and data analysis capabilities
- **API Requirements**: Requires a Dataiku DSS instance with API access enabled and appropriate API key credentials

## Limitations

- Requires a valid Dataiku DSS instance with API access
- Agent IDs must be in the format `agent:xxxxxxxx`
- Streaming responses collect all chunks before returning the final result (real-time streaming to SAM not yet implemented)
- API rate limits depend on your Dataiku instance configuration
- Network connectivity required between SAM and Dataiku instance

## Building and Running Custom Code Agents

### Prerequisites

- Python 3.10 or higher
- Dataiku API client library (`dataiku-api-client`)
- Access to a Dataiku DSS instance with API enabled

### Build Instructions

The plugin is automatically built when installed via SAM. For manual building:

```bash
cd dataiku-agent
pip install -e .
```

### Running the Agent

The agent runs as part of the SAM ecosystem. Ensure your environment variables are set:

```bash
export DATAIKU_INSTANCE_URL="https://your-instance.dataiku.com"
export DATAIKU_API_KEY="your-api-key"
export DATAIKU_DEFAULT_PROJECT="YOUR_PROJECT_KEY"

# Run SAM with your configuration
sam run configs/plugins/your-dataiku-agent.yaml
```

### Development

For local development:

```bash
# Install in development mode
cd dataiku-agent
pip install -e .

# Run tests (if available)
pytest tests/

# Check code style
black src/
flake8 src/
```

### Testing

To test the plugin functionality:

1. **Test Connection**:
   ```python
   from dataiku_agent.utils.dataiku_client import DataikuClient
   
   client = DataikuClient()
   assert client.test_connection()
   ```

2. **List Agents**:
   ```python
   agents = client.list_agents()
   print(f"Found {len(agents)} agents")
   ```

3. **Invoke Agent**:
   ```python
   result = client.invoke_agent(
       agent_id="agent:your_agent_id",
       message="Test message"
   )
   print(result)
   ```

--- 

## Original Author

Created by Solace Community

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## Changelog

### Version 0.1.0
- Initial release
- Support for invoking Dataiku agents
- Agent discovery and metadata retrieval
- Streaming and non-streaming response handling
- Comprehensive error handling
- Full SAM integration with A2A protocol support