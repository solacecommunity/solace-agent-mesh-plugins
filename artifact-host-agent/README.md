# Artifact Host Agent Plugin

An agent plugin for Solace Agent Mesh that hosts artifacts on a web server for easy access via URLs.

## Description

This plugin runs a Flask web server that makes artifacts accessible via HTTP. It automatically starts when the agent launches and provides tools to host artifacts with simple URLs for sharing and access.

## Features

### Web Server
- **Automatic Startup**: Web server starts when agent initializes
- **Background Operation**: Runs in a daemon thread, doesn't block agent
- **Directory Listing**: Browse all hosted files at the root URL
- **Direct File Access**: Access individual files via direct URLs
- **All File Types**: Supports images, PDFs, audio, video, documents, etc.

### File Hosting
- **Simple Tool**: Single `host_artifact` tool to make files accessible
- **Custom Filenames**: Optional custom naming for hosted files
- **Version Support**: Host specific artifact versions
- **URL Generation**: Automatically generates access URLs
- **Firewall Support**: Configure custom base URL for proxy/firewall scenarios

## Requirements

- Python >= 3.10
- Flask >= 3.0.0
- Solace Agent Mesh framework

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=artifact-host-agent
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add artifact-host-agent --plugin artifact-host-agent`

## Configuration

### Default Configuration

The web server starts automatically with these defaults:
- **Host**: 127.0.0.1 (localhost only)
- **Port**: 8080
- **Directory**: `./hosted_files/` (relative to working directory)
- **Base URL**: `http://localhost:8080`

### Custom Configuration

Edit the `init_function` config in `config.yaml`:

```yaml
init_function:
  component_module: artifact_host_agent.lifecycle
  function_name: init_function
  config:
    port: 9000                    # Custom port
    host: "0.0.0.0"               # Bind to all interfaces
    host_directory: "/var/www/artifacts"  # Custom directory
    base_url: "https://myserver.com/artifacts"  # Custom base URL
```

### Firewall/Proxy Scenarios

If the agent runs behind a firewall or proxy, configure the `base_url` to reflect the external URL:

```yaml
init_function:
  config:
    base_url: "https://mycompany.com/artifacts"

tools:
  - tool_type: python
    function_name: host_artifact
    tool_config:
      base_url: "https://mycompany.com/artifacts"
```

Generated URLs will use this base instead of localhost.

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts. The web server starts automatically on agent launch.

### Accessing the Web Interface

**Directory Listing:**
```
http://localhost:8080/
```
Shows all hosted files with names and sizes.

**Individual Files:**
```
http://localhost:8080/photo.jpg
http://localhost:8080/report.pdf
http://localhost:8080/audio.mp3
```

### Example Prompts

#### Basic Hosting
- *"Host the photo.jpg file so I can access it"*
- *"Make this artifact available via URL"*
- *"Publish this file to the web server"*

#### Custom Filenames
- *"Host report.pdf as latest_report.pdf"*
- *"Publish this image with the name thumbnail.jpg"*
- *"Make this file available as summary.txt"*

#### Version Management
- *"Host version 2 of the analysis document"*
- *"Publish the previous version of this report"*
- *"Make version 3 of the image accessible"*

#### Sharing
- *"Share this image externally"*
- *"Give me a URL to access this PDF"*
- *"How can I share this file with others?"*

## Tool Details

### host_artifact

Hosts an artifact on the web server.

**Parameters:**
- `artifact_filename` (str, required): Artifact filename with optional version (e.g., "photo.jpg" or "photo.jpg:2")
- `custom_filename` (str, optional): Custom name for the hosted file

**Returns:**
- `status`: "success" or "error"
- `message`: Human-readable message
- `artifact_filename`: Original artifact name
- `artifact_version`: Version that was hosted
- `hosted_filename`: Name of the file on the web server
- `url`: Full URL to access the file

**Example Return:**
```json
{
  "status": "success",
  "message": "Artifact hosted successfully",
  "artifact_filename": "photo.jpg",
  "artifact_version": 1,
  "hosted_filename": "photo.jpg",
  "url": "http://localhost:8080/photo.jpg"
}
```

## Architecture

### Components

**Web Server** (`web_server.py`):
- Flask-based HTTP server
- Runs in background daemon thread
- Serves files from configurable directory
- Provides HTML directory listing

**Tools** (`tools.py`):
- `host_artifact`: Copies artifact to web directory
- Returns URL for access

**Lifecycle** (`lifecycle.py`):
- `init_function`: Starts web server on agent startup
- `cleanup_function`: Gracefully stops server on shutdown

### File Flow

1. User requests to host artifact
2. Tool loads artifact from artifact service
3. Tool copies artifact to web server directory
4. Tool generates and returns URL
5. Files are accessible via HTTP immediately

### Directory Structure

```
hosted_files/
├── photo.jpg
├── report.pdf
├── audio.mp3
├── video.mp4
└── document.docx
```

All hosted files are stored flat in the hosting directory.

## Development

### Debug Mode

For rapid development without rebuilding:

```bash
cd artifact-host-agent/src
sam run ../config.yaml
```

Changes to tools will be reflected immediately (but web server requires restart for changes).

### Testing the Web Server

Start the agent and verify:

```bash
# Check directory listing
curl http://localhost:8080/

# Host a test file
# (through agent interaction or tool call)

# Access hosted file
curl http://localhost:8080/test.txt
```

## Security Considerations

**Default Configuration:**
- Binds to localhost (127.0.0.1) only
- Not accessible from external networks
- Suitable for local development and testing

**Production Considerations:**
- Consider authentication if exposing externally
- Use HTTPS proxy (nginx, Apache) for production
- Implement access controls if needed
- Be cautious when binding to 0.0.0.0
- Review firewall rules

## Limitations

- Flask development server (not production-grade)
- No authentication/authorization
- No HTTPS support (use reverse proxy)
- Files stored flat (no directory hierarchy)
- No file cleanup/deletion tool (manual cleanup needed)

## Future Enhancements

Potential improvements:
- Add `unhost_artifact` tool to remove files
- Add `list_hosted_artifacts` tool
- Support for directory organization
- File expiration/TTL
- Access logging
- File upload capability
- Authentication support

## Troubleshooting

**Web server won't start:**
- Check if port is already in use
- Verify host_directory is writable
- Check logs for initialization errors

**Can't access hosted files:**
- Verify artifact was successfully hosted (check return status)
- Ensure web server is running
- Check URL is correct
- Verify firewall/network settings if accessing remotely

**Custom base_url not working:**
- Ensure it's configured in both `init_function` and tool `tool_config`
- Verify proxy/firewall is forwarding correctly
- Check URL format (include protocol: http:// or https://)

## License

See project license.

## Author

Greg Meldrum <greg.meldrum@solace.com>
