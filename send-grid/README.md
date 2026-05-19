# SendGrid SAM Plugin

SendGrid Agent for sending transactional and marketing emails through the SendGrid email delivery platform.

[SendGrid](https://sendgrid.com/)

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The SendGrid plugin enables SAM to send emails programmatically through SendGrid's email delivery service. This allows you to automate email notifications, send transactional emails, and integrate email communications directly into your SAM workflows. The plugin provides a simple interface for composing and sending emails with full HTML support.

## Features

This agent provides the following capabilities:

- **Transactional Email**: Send automated transactional emails
- **HTML Email Support**: Send rich HTML-formatted emails
- **Template Support**: Use SendGrid email templates
- **Delivery Tracking**: Leverage SendGrid's delivery and engagement tracking
- **Reliable Delivery**: Built on SendGrid's robust email infrastructure

## Video
<iframe width="560" height="315" src="https://www.youtube.com/embed/9VnFKJyWVZM?si=MjG4F9tL2VC5uZyy" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Configuration

The plugin requires the following environment variables to be set:

- `SENDGRID_API_KEY`: Your SendGrid API key
- `SENDGRID_FROM_EMAIL`: The default sender email address

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin send-grid`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=send-grid
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add send-grid --plugin send-grid`
4. Configure required environment variables (see Configuration section above)

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts to send emails.

### Example Prompts

- *"Send an email to user@example.com with the subject 'Welcome' and a greeting message"*
- *"Email the report to the team at team@company.com"*
- *"Send a notification email about the system update"*
- *"Compose and send a follow-up email to customer@example.com"*

## External Services

This plugin utilizes the following external service(s):

- **[SendGrid](https://sendgrid.com/)**: Cloud-based email delivery platform
- **API Requirements**: Requires SendGrid account with API key. Free tier available (up to 100 emails/day)

## Limitations

- Requires active SendGrid account with valid API key
- Email sending limits depend on your SendGrid plan
- Sender email must be verified in SendGrid
- Subject to SendGrid's sending policies and rate limits


## Building and Running Custom Code Agents

### Prerequisites

- Python 3.8 or higher
- pip package manager
- SendGrid account with API key

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

# Set environment variables
export SENDGRID_API_KEY="your_api_key_here"
export SENDGRID_FROM_EMAIL="sender@example.com"

# Run tests (if available)
pytest
```
---

## Original Author

Created by the Solace Community

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)


---

## Changelog

### Version 0.1.0
- Initial release
- Basic email sending functionality
- HTML email support
- SendGrid API integration
