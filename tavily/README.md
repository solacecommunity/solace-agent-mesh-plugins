# Tavily SAM Plugin

An agent for searching the web with Tavily AI's intelligent search API.

[Tavily AI](https://www.tavily.com/)

---

**Plugin Type:** `Wrapper Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The Tavily plugin enables SAM to perform intelligent web searches using Tavily AI's search API. This allows you to retrieve relevant, up-to-date information from the web directly through your SAM orchestrator. Tavily AI provides optimized search results specifically designed for AI agents and LLM applications, making it ideal for research, fact-checking, and information gathering tasks.

## Features

This agent provides the following capabilities:

- **AI-Optimized Search**: Get search results optimized for AI and LLM consumption
- **Real-Time Information**: Access current web data and information
- **Structured Results**: Receive search results in a structured, easy-to-parse format
- **Contextual Relevance**: Benefit from Tavily's AI-powered relevance ranking

## Video 
[![Watch the video](https://img.youtube.com/vi/rydMzt5QMEM/hqdefault.jpg)](https://www.youtube.com/embed/rydMzt5QMEM)
https://youtu.be/rydMzt5QMEM?si=YT5deKlrZI9AZRMI

## Configuration

The plugin requires the following environment variables to be set:

- `TAVILY_TOKEN`: Your Tavily API token

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin tavily`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=tavily
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add tavily --plugin tavily`
4. Configure required environment variables: `export TAVILY_TOKEN="your_api_key_here"`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts to search for information on the web.

### Example Prompts

- *"Search the web for the latest information about quantum computing"*
- *"Find recent news about artificial intelligence developments"*
- *"Look up current best practices for REST API design"*
- *"Search for information about climate change solutions"*

## External Services

This plugin utilizes the following external service(s):

- **[Tavily AI](https://www.tavily.com/)**: AI-optimized web search API
- **API Requirements**: Requires Tavily account with API token. Free trial available.

## Limitations

- Requires active Tavily account with valid API token
- Search rate limits depend on your Tavily plan
- Results are subject to Tavily's content policies
- Internet connectivity required for search operations

---

## Original Author

Created by the Solace Community

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## Changelog

### Version 0.1.0
- Initial release
- Tavily AI search integration
- Web search capabilities for SAM
