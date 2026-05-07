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
- `SOLACE_DEV_MODE`: Enable broker dev mode (default: `false`)
- `USE_TEMPORARY_QUEUES`: Use temporary broker queues (default: `true`)
- `CLI_ENTRYPOINT_ID`: Unique entrypoint ID for multi-instance setups (default: `sam-cli-ep-01`)
- `SAM_CLI_SESSIONS_DIR`: Directory for session index file (default: `~/.sam-cli-entrypoint`)

### Configuration File (`config.yaml`)

The `config.yaml` contains the entrypoint configuration including broker connection settings, adapter options, and artifact service setup. All configurable values are driven by environment variables with sensible defaults — edit your `.env` file or set the variables directly rather than modifying the YAML.

### Adapter Options

Configured under `adapter_config` in `config.yaml`:

| Option | Default | Description |
|---|---|---|
| `prompt_name` | `"sam"` | Name displayed in the REPL prompt (e.g., `sam [default]>`) |
| `show_status_updates` | `true` | Show agent progress updates |

> User identity defaults to `sam_dev_user` (provided by the SAM framework when no auth is configured) and is no longer surfaced via `adapter_config`.

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

**Recommended launch** — assign a unique entrypoint ID (so multiple terminals don't collide on the broker queue) and suppress SAM framework log chatter so the REPL output stays clean:

```bash
CLI_ENTRYPOINT_ID=cli-entrypoint-02 \
  LOGGING_SAC_LEVEL=ERROR \
  LOGGING_SAM_LEVEL=ERROR \
  LOGGING_SAM_TRACE_LEVEL=ERROR \
  sam run configs/gateways/cli-entrypoint.yaml
```

The three `LOGGING_*_LEVEL` vars correspond to the three logger channels SAM exposes: `solace_ai_connector` (SAC), `solace_agent_mesh` (SAM), and `sam_trace` (per-task agent traces). All three need to be set — leaving any one at its default (`INFO`) will leak chatter into the REPL.

For additional terminals, just bump the ID (`cli-entrypoint-03`, `cli-entrypoint-04`, …). Each running CLI must use its own `CLI_ENTRYPOINT_ID`.

### Suppressing SAM Log Output

The recommended launch above sets `LOGGING_SAC_LEVEL`, `LOGGING_SAM_LEVEL`, and `LOGGING_SAM_TRACE_LEVEL` to `ERROR` to silence all three SAM logger channels at the source. If a particularly noisy third-party library still leaks through, also set `LOGGING_ROOT_LEVEL=ERROR` (defaults to `WARNING`).

As an alternative to env vars, the plugin ships a `logging.yaml` that pins the console handler to ERROR and routes full DEBUG output to a rolling `cli-entrypoint.log` file:

```bash
LOGGING_CONFIG_PATH=configs/gateways/logging.yaml sam run configs/gateways/cli-entrypoint.yaml
```

**Tip:** wrap the recommended launch in a shell alias so you don't have to retype it:

```bash
alias sam-cli='CLI_ENTRYPOINT_ID=cli-entrypoint-02 LOGGING_SAC_LEVEL=ERROR LOGGING_SAM_LEVEL=ERROR LOGGING_SAM_TRACE_LEVEL=ERROR sam run configs/gateways/cli-entrypoint.yaml'
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
| `/switch <label\|id>` | Switch to an existing session (SAM reloads full history automatically) |
| `/rename <label>` | Rename the current session |
| `/delete <label\|id>` | Remove a session from the local index (conversation history and artifacts remain on SAM) |

#### Agents & Entrypoints

| Command | Description |
|---|---|
| `/agents` | List registered agents |
| `/entrypoints` | List connected entrypoints (type and last-seen age) |
| `/agent <name> <message>` | Send a message directly to a specific agent |

#### Files

| Command | Description |
|---|---|
| `/upload <file> [message]` | Send a file to an agent |
| `/artifacts` | List agent-created files in this session |
| `/download [artifact] [path]` | Save artifacts (Tab completes artifact names; interactive multi-select if no artifact given) |

#### History & Export

| Command | Description |
|---|---|
| `/history [count]` | Show conversation history for the current session (optionally last N entries) |
| `/export [format] [path]` | Export history to a file. Format: `md` (default), `json`, or `txt` |

#### Terminal

| Command | Description |
|---|---|
| `/retry` | Re-send the last message |
| `/clear` | Clear the screen |
| `/multiline` | Toggle multiline input (Alt+Enter to submit) |
| `/alias [name] [text]` | Create, list, or remove command aliases (cannot shadow built-ins) |
| `/help` | Show available commands |
| `/quit` (or `/exit`) | Exit the CLI |

#### Command Shortcuts

All commands support prefix matching — type the shortest unambiguous prefix and press Enter. With the current command set, examples include `/se` → `/sessions`, `/sw` → `/switch`, `/n` → `/new`, `/re` → `/rename`, `/de` → `/delete`, `/ar` → `/artifacts`, `/u` → `/upload`, `/do` → `/download`, `/m` → `/multiline`, `/c` → `/clear`, `/q` → `/quit`. Prefixes that are shared between commands (e.g. `/h` between `/help` and `/history`, `/ag` between `/agents` and `/agent`, `/e` between `/export` and `/exit`) require an extra letter to disambiguate.

#### How Sessions Work

Sessions are identified by an internal `session_id` that scopes both conversation history and artifacts on SAM's side. The entrypoint maintains a local index (`~/.sam-cli-entrypoint/sessions.json`) that maps human-readable labels to session IDs and tracks metadata (message counts, timestamps).

- **SAM is the source of truth** for conversation history and artifacts. The local index only stores labels and stats.
- **Switching sessions** changes the `session_id` passed to SAM. The agent automatically picks up the full history for that session — no manual reload needed.
- **Deleting a session** removes it from the local index only. SAM has no entrypoint-facing API to delete server-side history.
- **Sessions persist across restarts.** On launch, the entrypoint restores the last active session from the index.

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

Created by Giri Venkatesan (SolaceLabs)

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
- Direct-to-agent messaging (`/agent`), connected entrypoints listing (`/entrypoints`), and command aliases (`/alias`)
- In-session history and export to md/json/txt (`/history`, `/export`)
- Terminal helpers: `/retry`, `/clear`, `/multiline`
- Safe behaviour during multi-config `sam run` invocations (skips REPL/broker binding)
