# Bright Data SAM Plugin

An agent to discover, access, extract and interact with any public website via Bright Data's web scraping and data collection platform.

[Bright Data](https://brightdata.com/)

---

**Plugin Type:** `Wrapper Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The Bright Data plugin enables SAM to interact with Bright Data's web scraping and data collection services. This allows you to extract data from websites, access public web data, and perform web intelligence gathering tasks directly through your SAM orchestrator. The plugin leverages Bright Data's robust infrastructure for reliable and compliant data collection.

## Features

This agent provides the following capabilities:

- **Web Scraping**: Extract structured data from websites
- **Data Collection**: Access public web data at scale
- **Website Interaction**: Automate interactions with web pages
- **Proxy Networks**: Leverage Bright Data's proxy infrastructure for reliable access

## Video 
[![Watch the video](https://img.youtube.com/vi/FkDqEZ_WvyE/hqdefault.jpg)](https://youtu.be/FkDqEZ_WvyE?si=tnISgkKROm2VG-Cz)
https://youtu.be/FkDqEZ_WvyE?si=tnISgkKROm2VG-Cz


## Configuration

The plugin requires the following environment variables to be set:

- `BRIGHTDATA_TOKEN`: Your Bright Data MCP server API token

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin bright-data`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=bright-data
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add bright-data --plugin bright-data`
4. Configure required environment variables: `export BRIGHTDATA_TOKEN="your_api_key_here"`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts to request web data extraction and website interactions.

### Example Prompts

- *"Extract product listings from this e-commerce website"*
- *"Get the latest news articles from this site"*
- *"Scrape pricing data from competitor websites"*
- *"Collect public reviews from this page"*

## External Services

This plugin utilizes the following external service(s):

- **[Bright Data](https://brightdata.com/)**: Web scraping and data collection platform
- **API Requirements**: Requires Bright Data account with API token. Free trial available.

## Limitations

- Requires active Bright Data account
- Usage limits depend on your Bright Data plan
- Must comply with website terms of service and applicable laws
- Rate limits apply based on your subscription tier

---

## Original Author

Created by the Jamieson Walker

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## Changelog

### Version 0.1.0
- Initial release
- Bright Data MCP server integration
- Web scraping and data extraction support
