# SMTP Gateway SAM Plugin

Comprehensive email management agent for sending and receiving emails with attachments through SMTP/IMAP protocols.

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The SMTP Gateway plugin provides comprehensive email management capabilities for SAM, enabling agents to send and receive emails with attachments through standard SMTP and IMAP protocols. This plugin offers a complete email solution with support for HTML emails, file attachments, folder management, and advanced email operations.

Unlike simple email-sending services, this plugin provides full bidirectional email communication, allowing your agents to both send outgoing emails and monitor incoming messages. It's ideal for automated email workflows, notification systems, customer communication, and any scenario requiring programmatic email management.

## Features

This agent provides the following capabilities:

- **Email Sending**: Send emails with HTML or plain text content via SMTP
- **Attachment Support**: Attach files to outgoing emails with automatic MIME type detection
- **Email Receiving**: Retrieve and read emails from IMAP servers with flexible filtering
- **Attachment Download**: Download and save email attachments to local storage
- **Email Management**: Mark emails as read/unread, delete emails, move between folders
- **Folder Operations**: List and navigate IMAP folder structures
- **Security Features**: TLS/SSL encryption, email validation, file size limits, MIME type detection
- **CC/BCC Support**: Send emails to multiple recipients with carbon copy options
- **Search Capabilities**: Filter emails by sender, subject, read status, and custom criteria

## Configuration

The plugin requires the following environment variables to be set:

### SMTP Configuration (for sending emails)
- `SMTP_HOST`: SMTP server hostname (e.g., smtp.gmail.com)
- `SMTP_PORT`: SMTP server port (default: 587 for TLS)
- `SMTP_USERNAME`: SMTP authentication username
- `SMTP_PASSWORD`: SMTP authentication password
- `SMTP_USE_TLS`: Use TLS encryption (default: true)

### IMAP Configuration (for receiving emails)
- `IMAP_HOST`: IMAP server hostname (e.g., imap.gmail.com)
- `IMAP_PORT`: IMAP server port (default: 993 for SSL)
- `IMAP_USERNAME`: IMAP authentication username
- `IMAP_PASSWORD`: IMAP authentication password
- `IMAP_USE_SSL`: Use SSL encryption (default: true)

### Optional Configuration
- `ATTACHMENT_DOWNLOAD_PATH`: Directory for downloaded attachments (default: /tmp/email_attachments)

**Note:** For many email providers (Gmail, Outlook, etc.), the SMTP and IMAP credentials are the same.

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin smtp-gateway`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=smtp-gateway
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add smtp-gateway --plugin smtp-gateway`
4. Configure required environment variables (see Configuration section above)

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts for email operations.

### Example Prompts

**Sending Emails:**
- *"Send an email to john@example.com with subject 'Meeting Tomorrow' and body 'Let's meet at 2pm'"*
- *"Email the quarterly report to team@company.com with the PDF file attached"*
- *"Send an HTML email to customer@example.com with our new product announcement"*
- *"Send an email to alice@example.com and CC bob@example.com about the project update"*

**Receiving Emails:**
- *"Check my inbox for new emails"*
- *"Show me the last 5 unread emails"*
- *"Find emails from support@example.com in my inbox"*
- *"List emails with 'invoice' in the subject"*

**Managing Emails:**
- *"Download the attachment from email ID 123"*
- *"Mark email ID 456 as read"*
- *"Delete email ID 789"*
- *"Move email ID 321 to the Archive folder"*
- *"List all my email folders"*

### Tools Available

The agent includes the following tools:

- **`send_email`**: Send an email with optional attachments, CC, and BCC recipients
- **`receive_emails`**: Retrieve emails from a folder with filtering options
- **`download_attachment`**: Download a specific attachment from an email
- **`mark_email_read`**: Mark an email as read or unread
- **`delete_email`**: Permanently delete an email
- **`move_email`**: Move an email to a different folder
- **`list_folders`**: List all available IMAP folders

## External Services

This plugin utilizes standard email protocols and does not depend on specific external services:

- **SMTP Protocol**: Standard protocol for sending emails (RFC 5321)
- **IMAP Protocol**: Standard protocol for receiving emails (RFC 3501)
- **Compatible with**: Gmail, Outlook, Yahoo Mail, custom mail servers, and any SMTP/IMAP-compliant email service

## Security Considerations

- **Encryption**: All connections use TLS/SSL encryption by default
- **Credential Storage**: Credentials are stored in environment variables only
- **Email Validation**: All email addresses are validated before processing
- **Attachment Limits**: Default 25MB size limit on attachments (configurable)
- **File Type Detection**: Automatic MIME type detection for attachments
- **Input Sanitization**: Email content is sanitized to prevent injection attacks

## Limitations

- Attachment size limited to 25MB by default (configurable)
- Requires valid SMTP and IMAP server credentials
- Subject to email provider rate limits and policies
- Some email providers require app-specific passwords (e.g., Gmail with 2FA)
- IMAP operations require the email server to support IMAP protocol

## Building and Running Custom Code Agents

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Valid SMTP and IMAP server credentials

### Build Instructions

```bash
# Navigate to plugin directory
cd smtp-gateway

# Install dependencies
pip install -e .
```

### Running the Agent

The agent runs as part of SAM. After installation, SAM will automatically manage the agent lifecycle.

### Development

For local development:

```bash
# Install in development mode
pip install -e .

# Set environment variables
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export IMAP_HOST="imap.gmail.com"
export IMAP_PORT="993"
export IMAP_USERNAME="your-email@gmail.com"
export IMAP_PASSWORD="your-app-password"

# Run tests (if available)
pytest tests/
```

### Gmail Configuration Example

For Gmail users, you'll need to:
1. Enable 2-factor authentication on your Google account
2. Generate an app-specific password at https://myaccount.google.com/apppasswords
3. Use these settings:
   - SMTP_HOST: smtp.gmail.com
   - SMTP_PORT: 587
   - IMAP_HOST: imap.gmail.com
   - IMAP_PORT: 993
   - Use your app-specific password for both SMTP_PASSWORD and IMAP_PASSWORD

---

## Original Author

Created by the Solace Community

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## Changelog

### Version 0.1.0
- Initial release
- SMTP email sending with attachments
- IMAP email receiving with filters
- Attachment download functionality
- Email management operations (mark read, delete, move)
- Folder listing and navigation
- TLS/SSL security
- Email validation
- Comprehensive error handling
