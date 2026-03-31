# Find My IP SAM Plugin

A Solace Agent Mesh plugin that provides comprehensive IP address information services including current IP detection, geolocation lookup, and security analysis.

[IPify API Documentation](https://ipify.org/)

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The Find My IP agent is designed to help users understand their current network location and connection details. It provides accurate IP address information, geolocation data, and security analysis to support location-based queries and network security assessments. This plugin integrates multiple reliable APIs to ensure redundancy and comprehensive data coverage for IP-based intelligence gathering within your SAM workflows.

## Features

This agent provides the following capabilities:

- **Current IP Detection**: Retrieve your current public IP address from reliable APIs
- **Geolocation Services**: Get detailed location information including country, city, region, and coordinates
- **Security Analysis**: Analyze IP addresses for security characteristics including proxy, VPN, TOR, and crawler detection
- **Comprehensive Information**: Provide detailed connection and network information
- **Multi-API Support**: Uses multiple reliable APIs for redundancy and accuracy

## Configuration

This plugin does not require any environment variables or API keys. It uses free public APIs.

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin find-my-ip`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=find-my-ip
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add find-my-ip --plugin find-my-ip`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts.

### Example Prompts

#### Basic IP Information
- *"What is my current IP address?"*
- *"Show me my public IP"*
- *"Get my IP address"*

#### Location-Based Queries
- *"Where am I located?"*
- *"What city am I in?"*
- *"What country is my IP from?"*
- *"Show me my coordinates"*

#### Security Analysis
- *"Is my connection secure?"*
- *"Am I using a VPN or proxy?"*
- *"Analyze my IP for security characteristics"*
- *"Check if my IP is flagged as suspicious"*

#### Comprehensive Information
- *"Give me all details about my IP"*
- *"Show me comprehensive IP information"*
- *"What are my connection details?"*

#### Specific IP Analysis
- *"Where is the IP address 8.8.8.8 located?"*
- *"Analyze the security of IP 192.168.1.1"*
- *"Get location information for 1.1.1.1"*

### Tools Available

The agent includes the following tools:

- **`get_current_ip`**: Retrieves the current public IP address from reliable APIs
- **`get_ip_with_retry`**: Gets current IP address with retry logic for improved reliability
- **`get_ip_info`**: Retrieves IP address with optional location information
- **`get_ip_comprehensive_info`**: Provides comprehensive IP information including security, connection, and location data
- **`get_ip_security_info`**: Analyzes IP address for security characteristics including proxy, VPN, TOR, and crawler detection
- **`get_ip_location`**: Gets detailed location information for a given IP address using multiple APIs

## External Services

This plugin utilizes the following external service(s):

- **[IPify](https://ipify.org/)**: Free IP address detection service
- **[ipapi.co](https://ipapi.co/)**: Comprehensive geolocation API
- **[ip-api.com](http://ip-api.com/)**: Free IP geolocation service
- **[ipinfo.io](https://ipinfo.io/)**: IP geolocation and information service
- **[ipwhois.io](https://ipwhois.io/)**: IP geolocation and WHOIS data
- **API Requirements**: Free tier available, no API key required

## Limitations

- **Rate Limits**: Some APIs have rate limits (handled automatically)
- **IPv6 Support**: Limited IPv6 support in some APIs
- **Privacy**: IP-based location is approximate and may not reflect exact physical location
- **Network Dependencies**: Requires internet connection for API access

## Error Handling

The agent includes robust error handling:

- **Retry Logic**: Automatic retry for failed API calls
- **Fallback APIs**: Multiple API sources for redundancy
- **Graceful Degradation**: Continues operation even if some services are unavailable
- **Clear Error Messages**: Informative error reporting to users


## Building and Running Custom Code Agents

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Build Instructions

```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Agent

The agent runs as part of SAM. After installation, SAM will automatically manage the agent lifecycle.

### Development

For local development:

```bash
# Install in development mode
pip install -e .

# Run tests (if available)
pytest
```
---

## Original Author

Created by the Giri Venkatesan

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)


---

## Changelog

### Version 0.1.0
- Initial release
- Basic IP detection and geolocation
- Security analysis capabilities
- Multi-API support for reliability
