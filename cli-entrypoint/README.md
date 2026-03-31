# CLI Entrypoint SAM Plugin

A terminal-based entrypoint for [Solace Agent Mesh](https://github.com/SolaceLabs/solace-agent-mesh). Chat with SAM agents directly from your command line.

[Solace Agent Mesh Documentation](https://github.com/SolaceLabs/solace-agent-mesh)

---

**Plugin Type:** `Gateway`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) and is not officially supported by Solace. For community support, please open an issue in this repository. 
⭐️ Please leave a star on the [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) repo while you are there. 

---

## Overview

The CLI Entrypoint plugin provides a terminal-based interface for interacting with Solace Agent Mesh agents. It acts as a first-class SAM entrypoint — just like the built-in WebUI or Slack entrypoints — but routes messages through an interactive REPL in your terminal.

It is built on SAM's `BaseGatewayApp` + `BaseGatewayComponent` pattern, translating stdin to A2A protocol parts on the way in and rendering agent responses as styled markdown on the way out. The CLI entrypoint makes zero LLM calls; all intelligence lives on the agent side.

This plugin is ideal for developers who prefer terminal workflows, CI/CD integration, or headless environments where a browser-based UI is impractical.

## Features

This entrypoint provides the following capabilities:

- **Interactive REPL**: Tab auto-completion for commands, session labels, and artifact names
- **Markdown Rendering**: Agent responses rendered with headings, code blocks, tables, and bullets via Rich
- **Multi-Session Support**: Create, name, switch between, and manage multiple concurrent sessions that persist across restarts
- **File Upload**: Send local files to agents for analysis
- **Artifact Management**: List and download agent-created files, scoped per session
- **Graceful Exit**: Exit via `/quit` or Ctrl+D

## Configuration

The plugin requires the following environment variables to be set:

- `NAMESPACE`: Your SAM namespace (e.g., `my-org/dev`) *(required)*
- `SOLACE_BROKER_URL`: Solace broker WebSocket URL (default: `ws://localhost:8008`)
- `SOLACE_BROKER_USERNAME`: Broker username (default: `default`)
- `SOLACE_BROKER_PASSWORD`: Broker password (default: `default`)
- `SOLACE_BROKER_VPN`: Broker VPN name (default: `default`)
- `CLI_ENTRYPOINT_USER`: User identity for this session (default: `cli_entrypoint_user`)
- `CLI_ENTRYPOINT_ID`: Unique entrypoint ID for multi-instance setups (default: `sam-cli-ep-01`)
- `SAM_CLI_SESSIONS_DIR`: Directory for session index file (default: `~/.sam-cli-entrypoint`)

### Configuration File (`config.yaml`)

The `config.yaml` contains the entrypoint configuration including broker connection settings, adapter options, and artifact service setup. All configurable values are driven by environment variables with sensible defaults — edit your `.env` file or set the variables directly rather than modifying the YAML.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=cli-entrypoint
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add cli-entrypoint --plugin cli-entrypoint`
4. Configure required environment variables (see Configuration section above)

## Usage

Once installed, run the entrypoint with:

```bash
sam run config.yaml
```

For multiple instances, set a unique entrypoint ID per terminal:

```bash
CLI_ENTRYPOINT_ID=sam-cli-ep-01 sam run config.yaml
CLI_ENTRYPOINT_ID=sam-cli-ep-02 sam run config.yaml  # second terminal
```

### Example Prompts

- *"What agents are available?"*
- *"Summarize the contents of this file" (after using `/upload`)*
- *"Create a report on recent sales data"*
- *"List all artifacts from this session"*

### REPL Commands

#### Sessions

| Command | Description |
|---|---|
| `/new [label]` | Start a new session, optionally named |
| `/sessions` | List all sessions with message counts and last active time |
| `/switch <label\|id>` | Switch to an existing session |
| `/rename <label>` | Rename the current session |
| `/delete <label\|id>` | Remove a session from the local index |

#### General

| Command | Description |
|---|---|
| `/agents` | List registered agents |
| `/upload <file> [message]` | Send a file to an agent |
| `/artifacts` | List agent-created files in this session |
| `/download [artifact] [path]` | Save artifacts (Tab completes artifact names) |
| `/help` | Show available commands |
| `/quit` | Exit the CLI |

All commands support prefix matching (e.g., `/s` → `/sessions`, `/sw` → `/switch`).

## External Services

This plugin utilizes the following external service(s):

- **[Solace PubSub+ Event Broker](https://solace.com/products/event-broker/)**: Message broker for routing A2A protocol messages between the CLI entrypoint and SAM agents
- **API Requirements**: A running Solace broker instance (local or cloud) with WebSocket access

## Limitations

- Deleting a session removes it from the local index only; SAM has no entrypoint-facing API to delete server-side history or artifacts
- The CLI takes over stdin — run it in its own `sam run` process, not bundled with other entrypoints
- Rich markdown rendering depends on terminal capabilities; output may vary across terminal emulators

## Setup

### Prerequisites

- Python 3.10+
- A running Solace Agent Mesh environment with broker access
- `solace-agent-mesh` package installed

### Build Instructions

```bash
# Install into your SAM project's virtual environment
pip install -e .
```

### Running the Entrypoint

```bash
# Copy and configure environment
cp .env.example .env

# Run via Solace Agent Mesh
sam run config.yaml
```

--- 

## Original Author

Created by Giri Venkatesan

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)


---

## Changelog

### Version 0.1.0
- Initial release
- Interactive REPL with Tab auto-completion
- Multi-session support with local session index
- Markdown rendering via Rich
- File upload and artifact management
- Prefix matching for commands
