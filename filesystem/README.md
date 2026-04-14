# Filesystem SAM Plugin

Secure file operations with configurable access controls through the Model Context Protocol (MCP).

[MCP Filesystem Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)

---

**Plugin Type:** `Wrapper Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The Filesystem plugin provides SAM with secure, controlled access to file system operations through the official Model Context Protocol (MCP) Filesystem server. This plugin enables AI agents to read, write, search, and manage files and directories within specified, allowed paths. The MCP Filesystem server implements comprehensive security measures including path validation, directory traversal prevention, and configurable access controls.

With this plugin, your SAM agents can interact with the local file system to assist with code editing, file management, documentation generation, log analysis, and many other file-related tasks.

## Features

This agent provides the following capabilities:

- **Secure File Reading**: Read file contents from allowed directories with automatic encoding detection
- **File Writing**: Create and update files within configured paths
- **Directory Operations**: List directory contents, create directories, and navigate file structures
- **File Search**: Search for files using glob patterns and regular expressions
- **File Metadata**: Access file information including size, permissions, and modification times
- **File Management**: Move, copy, and organize files within allowed boundaries
- **Path Validation**: Built-in security to prevent directory traversal and unauthorized access
- **Multiple Format Support**: Handle text files, JSON, YAML, and other common formats

## Configuration

The plugin requires the following environment variables to be set:

- `FILESYSTEM_ALLOWED_PATH`: The root directory path that the filesystem agent is allowed to access (e.g., `/home/user/projects` or `C:\Users\username\Documents`)

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin filesystem`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

**Important Configuration Note**: The filesystem server requires at least one allowed directory path to be specified. This is passed via the `FILESYSTEM_ALLOWED_PATH` environment variable and serves as the root of accessible paths for security.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=filesystem
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add filesystem --plugin filesystem`
4. Configure required environment variable: `export FILESYSTEM_ALLOWED_PATH="/path/to/allowed/directory"`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts to perform file operations.

### Example Prompts

- *"Read the contents of the config.json file"*
- *"List all Python files in the src directory"*
- *"Create a new file called notes.txt with this content: [your text]"*
- *"Search for all markdown files containing the word 'tutorial'"*
- *"Get information about the package.json file"*
- *"Move the old_data.csv file to the archive folder"*

### Tools Available

The agent includes the following tool categories:

- **`read_file`**: Read the complete contents of a file
- **`read_multiple_files`**: Read multiple files in a single operation
- **`write_file`**: Create or overwrite a file with new contents
- **`edit_file`**: Make targeted edits to existing files
- **`create_directory`**: Create new directories
- **`list_directory`**: List contents of a directory
- **`directory_tree`**: Get a recursive tree view of directory structure
- **`move_file`**: Move or rename files
- **`search_files`**: Search for files using patterns
- **`get_file_info`**: Retrieve metadata about a file
- **`list_allowed_directories`**: See which directories are accessible

## External Services

This plugin utilizes the following external service(s):

- **[MCP Filesystem Server](https://github.com/modelcontextprotocol/servers)**: Official Model Context Protocol filesystem server implementation
- **Requirements**: Node.js runtime (npx) for executing the MCP server

## Limitations

- File operations are strictly limited to the configured allowed directories
- Large file operations may have performance implications
- Binary files are not directly supported for content reading
- Some operations require appropriate file system permissions
- The agent cannot access system files or directories outside the allowed path
- Maximum file size limits may apply depending on system resources

## Security Considerations

This plugin implements several security measures:

1. **Path Validation**: All file paths are validated to ensure they're within allowed directories
2. **Directory Traversal Prevention**: Protection against `../` and similar attacks
3. **Configurable Access**: Fine-grained control over which directories are accessible
4. **Audit Logging**: All file operations are logged for security auditing
5. **Error Isolation**: Errors don't expose sensitive system information

**Best Practices**:
- Always set `FILESYSTEM_ALLOWED_PATH` to the minimum necessary directory
- Regularly review file operation logs
- Use read-only mode when write access isn't needed
- Keep the MCP filesystem server package updated

---

## Original Author

Created by Leslie Fernando for the Solace Community

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## Changelog

### Version 0.1.0
- Initial release
- Integration with official MCP Filesystem server
- Secure file operations with configurable access controls
- Support for read, write, search, and directory operations
- Comprehensive error handling and logging
